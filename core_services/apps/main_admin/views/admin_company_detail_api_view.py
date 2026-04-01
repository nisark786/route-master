from django.db.models import Count, Q
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import NotFound

from apps.authentication.models import User
from apps.billing.models import CompanySubscription, PaymentTransaction
from apps.company.models import Company, CompanyActivityLog

from .base import SuperAdminAPIView


class AdminCompanyDetailAPIView(SuperAdminAPIView):
    @swagger_auto_schema(
        tags=["Main Admin"],
        operation_summary="Company detail",
        operation_description="Return profile, subscription, counts, payments, and activity logs for one company.",
        manual_parameters=[
            openapi.Parameter(
                "company_id",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            )
        ],
        responses={200: "Company detail", 401: "Unauthorized", 403: "Forbidden", 404: "Company not found"},
    )
    def get(self, request, company_id):
        company = Company.objects.filter(id=company_id).first()
        if not company:
            raise NotFound("Company not found.")

        subscription = CompanySubscription.objects.filter(company=company).select_related("plan").first()
        payments = PaymentTransaction.objects.filter(company=company)[:20]
        activity = CompanyActivityLog.objects.filter(company=company).select_related("actor")[:20]
        user_stats = User.objects.filter(company=company).aggregate(
            drivers_count=Count("id", filter=Q(role="DRIVER")),
            shops_count=Count("id", filter=Q(role="SHOP_OWNER")),
        )

        return self.success_response(
            data={
                "profile": {
                    "id": str(company.id),
                    "name": company.name,
                    "official_email": company.official_email,
                    "phone": company.phone,
                    "address": company.address,
                    "operational_status": company.operational_status,
                    "suspension_reason": company.suspension_reason,
                    "created_at": company.created_at,
                },
                "subscription": (
                    {
                        "plan_name": subscription.plan.name,
                        "plan_code": subscription.plan.code,
                        "status": "EXPIRED" if subscription.end_date < timezone.now() else "ACTIVE",
                        "start_date": subscription.start_date,
                        "end_date": subscription.end_date,
                        "amount_paid": str(subscription.amount_paid),
                    }
                    if subscription
                    else None
                ),
                "counts": {
                    "drivers": user_stats["drivers_count"] or 0,
                    "shops": user_stats["shops_count"] or 0,
                },
                "payment_history": [
                    {
                        "id": tx.id,
                        "payment_id": tx.payment_id,
                        "order_id": tx.order_id,
                        "amount": str(tx.amount),
                        "status": tx.status,
                        "invoice_number": tx.invoice_number,
                        "paid_at": tx.paid_at,
                    }
                    for tx in payments
                ],
                "activity_log": [
                    {
                        "id": log.id,
                        "action": log.action,
                        "actor": log.actor.email if log.actor else None,
                        "details": log.details,
                        "created_at": log.created_at,
                    }
                    for log in activity
                ],
            },
            message="Company detail loaded.",
        )
