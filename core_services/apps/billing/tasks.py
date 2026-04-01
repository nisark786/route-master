from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from apps.authentication.models import User
from apps.billing.models import CompanySubscription
from apps.company.models import Company, CompanyActivityLog


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_registration_otp_email_task(self, email, otp):
    ttl_minutes = max(int(getattr(settings, "REGISTRATION_OTP_TTL_SECONDS", 300)) // 60, 1)
    subject = "RouteMaster Company Registration OTP"
    body = f"Your OTP is {otp}. It is valid for {ttl_minutes} minutes."
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


def _clear_company_subscription_cache(company_id):
    cache.delete(f"billing:company-subscription-state:{company_id}")


def _expiry_email_recipients(company):
    recipients = set()
    if company.official_email:
        recipients.add(company.official_email.strip().lower())
    admin_emails = User.objects.filter(
        company_id=company.id,
        role="COMPANY_ADMIN",
        is_active=True,
    ).values_list("email", flat=True)
    recipients.update(email.strip().lower() for email in admin_emails if email)
    return sorted(recipients)


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def enforce_subscription_lifecycle_task(self):
    now = timezone.now()
    expired_subscriptions = (
        CompanySubscription.objects.select_related("company", "plan")
        .filter(is_active=True, end_date__lt=now)
        .order_by("end_date")
    )

    updated_count = 0
    for subscription in expired_subscriptions:
        with transaction.atomic():
            subscription.is_active = False
            subscription.save(update_fields=["is_active"])

            company = subscription.company
            if company.operational_status != Company.STATUS_SUSPENDED or company.is_active:
                company.operational_status = Company.STATUS_SUSPENDED
                company.is_active = False
                company.suspension_reason = "Subscription expired."
                company.save(update_fields=["operational_status", "is_active", "suspension_reason", "updated_at"])

            CompanyActivityLog.objects.create(
                company=company,
                actor=None,
                action="SUBSCRIPTION_EXPIRED_AUTO_SUSPEND",
                details={
                    "plan_code": subscription.plan.code,
                    "subscription_end_date": subscription.end_date.isoformat(),
                },
            )
            _clear_company_subscription_cache(company.id)
            cache.delete(f"company_profile:{company.id}")
            updated_count += 1

    return {"expired_and_suspended": updated_count}


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def send_subscription_expiry_reminders_task(self):
    now = timezone.now()
    reminder_days = (3, 1, 0)
    sent = 0

    for days_left in reminder_days:
        start_at = now + timedelta(days=days_left)
        end_at = start_at + timedelta(days=1)
        subscriptions = (
            CompanySubscription.objects.select_related("company", "plan")
            .filter(is_active=True, end_date__gte=start_at, end_date__lt=end_at)
            .order_by("end_date")
        )
        for subscription in subscriptions:
            recipients = _expiry_email_recipients(subscription.company)
            if not recipients:
                continue
            subject = "RouteMaster Subscription Expiry Reminder"
            body = (
                f"Hello,\n\n"
                f"Your subscription plan '{subscription.plan.name}' for company '{subscription.company.name}' "
                f"is scheduled to expire on {subscription.end_date.strftime('%Y-%m-%d %H:%M UTC')}.\n"
                f"Days left: {days_left}\n\n"
                f"Please renew to avoid interruption.\n"
            )
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipients,
                fail_silently=False,
            )
            sent += 1

    return {"reminders_sent": sent}
