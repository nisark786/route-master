import logging
import random
import threading
from decimal import Decimal, ROUND_HALF_UP
from django.core.cache import cache
from django.contrib.auth.hashers import check_password, make_password
import razorpay
from django.conf import settings
from django.core.mail import send_mail
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)


def get_razorpay_client():
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def generate_otp():
    return f"{random.randint(0, 999999):06d}"


def hash_otp(otp):
    return make_password(otp)


def verify_hashed_otp(raw_otp, hashed_otp):
    if not raw_otp or not hashed_otp:
        return False
    return check_password(raw_otp, hashed_otp)


def _otp_cache_ttl_seconds():
    return int(getattr(settings, "REGISTRATION_OTP_TTL_SECONDS", 300))


def _otp_cache_key(registration_id):
    return f"billing:registration_otp:{registration_id}"


def store_registration_otp(registration_id, otp):
    hashed = hash_otp(otp)
    cache.set(_otp_cache_key(registration_id), hashed, timeout=_otp_cache_ttl_seconds())


def get_registration_otp_hash(registration_id):
    return cache.get(_otp_cache_key(registration_id))


def delete_registration_otp(registration_id):
    cache.delete(_otp_cache_key(registration_id))


def send_registration_otp(email, otp):
    ttl_minutes = max(_otp_cache_ttl_seconds() // 60, 1)
    subject = "RouteMaster Company Registration OTP"
    body = f"Your OTP is {otp}. It is valid for {ttl_minutes} minutes."
    send_mail(
        subject=subject,
        message=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


def queue_registration_otp(email, otp):
    if not getattr(settings, "SEND_OTP_ASYNC", False):
        send_registration_otp(email, otp)
        return

    try:
        from .tasks import send_registration_otp_email_task
        send_registration_otp_email_task.apply_async((email, otp), retry=False, ignore_result=True)
    except Exception:
        logger.exception("Async OTP dispatch failed; falling back to direct email send.")
        send_registration_otp(email, otp)


def dispatch_registration_otp_background(email, otp):
    def _runner():
        try:
            queue_registration_otp(email, otp)
        except Exception:
            logger.exception("Background OTP dispatch failed for %s", email)

    threading.Thread(
        target=_runner,
        name=f"registration-otp-{email}",
        daemon=True,
    ).start()


def create_subscription_order(plan, receipt):
    client = get_razorpay_client()
    amount_paise = int((Decimal(plan.price) * Decimal("100")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    order_data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": receipt,
        "payment_capture": 1,
    }
    return client.order.create(data=order_data)


def verify_razorpay_signature(order_id, payment_id, signature):
    client = get_razorpay_client()
    client.utility.verify_payment_signature(
        {
            "razorpay_order_id": order_id,
            "razorpay_payment_id": payment_id,
            "razorpay_signature": signature,
        }
    )


def generate_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    refresh["role"] = user.role
    refresh["company_id"] = str(user.company_id) if user.company_id else None
    return {"refresh": str(refresh), "access": str(refresh.access_token)}


def get_cached_active_plans():
    from .models import SubscriptionPlan
    key = "billing:active_plans"
    cached = cache.get(key)
    if cached is not None:
        return cached

    plans = list(SubscriptionPlan.objects.filter(is_active=True).order_by("price"))
    cache.set(key, plans, timeout=300)
    return plans


def invalidate_active_plans_cache():
    cache.delete("billing:active_plans")
