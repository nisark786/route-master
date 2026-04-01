from django.db.models import Count, Q, Sum
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema

from apps.authentication.models import User
from apps.billing.models import CompanySubscription, PaymentTransaction
from apps.company.models import Company

from .base import SuperAdminAPIView, safe_decimal


class AdminOverviewAPIView(SuperAdminAPIView):
    @swagger_auto_schema(
        tags=["Main Admin"],
        operation_summary="Dashboard overview",
        operation_description="Return top-level KPI metrics for the executive dashboard.",
        responses={200: "Overview metrics", 401: "Unauthorized", 403: "Forbidden"},
    )
    def get(self, request):
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        company_stats = Company.objects.aggregate(
            total_companies=Count("id"),
            active_companies=Count(
                "id",
                filter=Q(operational_status=Company.STATUS_ACTIVE, is_active=True),
            ),
        )
        subscription_stats = CompanySubscription.objects.aggregate(
            active_subscriptions=Count("id", filter=Q(is_active=True, end_date__gte=now)),
            trial_companies=Count("id", filter=Q(plan__code="trial", is_active=True)),
            expired_subscriptions=Count("id", filter=Q(end_date__lt=now) | Q(is_active=False)),
        )

        revenue_stats = PaymentTransaction.objects.aggregate(
            monthly_revenue=Sum(
                "amount",
                filter=Q(status=PaymentTransaction.STATUS_SUCCESS, paid_at__gte=month_start),
            ),
            lifetime_revenue=Sum(
                "amount",
                filter=Q(status=PaymentTransaction.STATUS_SUCCESS),
            ),
        )
        monthly_revenue = safe_decimal(revenue_stats["monthly_revenue"])
        lifetime_revenue = safe_decimal(revenue_stats["lifetime_revenue"])

        user_stats = User.objects.aggregate(
            total_drivers=Count("id", filter=Q(role="DRIVER")),
            active_drivers=Count("id", filter=Q(role="DRIVER", is_active=True)),
            total_shops=Count("id", filter=Q(role="SHOP_OWNER")),
            active_shops=Count("id", filter=Q(role="SHOP_OWNER", is_active=True)),
        )

        return self.success_response(
            data={
                "total_companies": company_stats["total_companies"] or 0,
                "active_companies": company_stats["active_companies"] or 0,
                "active_subscriptions": subscription_stats["active_subscriptions"] or 0,
                "trial_companies": subscription_stats["trial_companies"] or 0,
                "expired_subscriptions": subscription_stats["expired_subscriptions"] or 0,
                "monthly_revenue": str(monthly_revenue),
                "lifetime_revenue": str(lifetime_revenue),
                "total_drivers": user_stats["total_drivers"] or 0,
                "active_drivers": user_stats["active_drivers"] or 0,
                "total_shops": user_stats["total_shops"] or 0,
                "active_shops": user_stats["active_shops"] or 0,
            },
            message="Dashboard overview loaded.",
        )
