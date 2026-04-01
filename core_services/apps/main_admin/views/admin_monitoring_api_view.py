from datetime import timedelta

from django.db.models import Sum
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema

from apps.billing.models import CompanySubscription, PaymentTransaction
from apps.company.models import Company

from .base import SuperAdminAPIView


class AdminMonitoringAPIView(SuperAdminAPIView):
    @swagger_auto_schema(
        tags=["Main Admin"],
        operation_summary="Subscription monitoring",
        operation_description="Return expiring/expired, high-value, and inactive company monitoring lists.",
        responses={200: "Monitoring datasets"},
    )
    def get(self, request):
        now = timezone.now()
        in_7_days = now + timedelta(days=7)

        expiring = CompanySubscription.objects.select_related("company", "plan").filter(
            end_date__gte=now, end_date__lte=in_7_days, is_active=True
        )[:20]
        expired = CompanySubscription.objects.select_related("company", "plan").filter(
            end_date__lt=now
        )[:20]

        high_value = (
            PaymentTransaction.objects.filter(status=PaymentTransaction.STATUS_SUCCESS)
            .values("company_id", "company__name")
            .annotate(total_spend=Sum("amount"))
            .order_by("-total_spend")[:20]
        )

        inactivity_cutoff = now - timedelta(days=30)
        long_inactive = Company.objects.filter(
            updated_at__lt=inactivity_cutoff
        ).order_by("updated_at")[:20]

        return self.success_response(
            data={
                "expiring_in_7_days": [
                    {
                        "company_id": str(item.company_id),
                        "company_name": item.company.name,
                        "plan_name": item.plan.name,
                        "end_date": item.end_date,
                    }
                    for item in expiring
                ],
                "expired_not_renewed": [
                    {
                        "company_id": str(item.company_id),
                        "company_name": item.company.name,
                        "plan_name": item.plan.name,
                        "end_date": item.end_date,
                    }
                    for item in expired
                ],
                "high_value_customers": [
                    {
                        "company_id": str(item["company_id"]),
                        "company_name": item["company__name"],
                        "total_spend": str(item["total_spend"] or 0),
                    }
                    for item in high_value
                ],
                "long_inactive_companies": [
                    {
                        "company_id": str(item.id),
                        "company_name": item.name,
                        "updated_at": item.updated_at,
                    }
                    for item in long_inactive
                ],
            },
            message="Monitoring data loaded.",
        )
