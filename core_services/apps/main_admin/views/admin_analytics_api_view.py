from django.core.cache import cache
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema

from apps.billing.models import CompanySubscription, PaymentTransaction
from apps.company.models import Company

from .base import SuperAdminAPIView, safe_decimal


def _month_start(dt):
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _add_months(dt, months):
    month_index = dt.month - 1 + months
    year = dt.year + month_index // 12
    month = month_index % 12 + 1
    return dt.replace(year=year, month=month, day=1)


class AdminAnalyticsAPIView(SuperAdminAPIView):
    @swagger_auto_schema(
        tags=["Main Admin"],
        operation_summary="Revenue and growth analytics",
        operation_description="Return MRR/ARR, churn, conversion, and chart datasets.",
        responses={200: "Analytics metrics", 401: "Unauthorized", 403: "Forbidden"},
    )
    def get(self, request):
        cache_key = "main_admin:analytics:v1"
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return self.success_response(data=cached_payload, message="Analytics loaded.")

        now = timezone.now()
        month_start = _month_start(now)

        mrr = safe_decimal(
            PaymentTransaction.objects.filter(
                status=PaymentTransaction.STATUS_SUCCESS, paid_at__gte=month_start
            ).aggregate(total=Sum("amount"))["total"]
        )
        arr = mrr * 12

        start_window = _add_months(month_start, -11)
        end_window = _add_months(month_start, 1)

        subs_by_month = {
            _month_start(item["month"]): item["count"]
            for item in CompanySubscription.objects.filter(
                start_date__gte=start_window,
                start_date__lt=end_window,
            )
            .annotate(month=TruncMonth("start_date"))
            .values("month")
            .annotate(count=Count("id"))
        }
        revenue_by_month = {
            _month_start(item["month"]): float(item["total"] or 0)
            for item in PaymentTransaction.objects.filter(
                status=PaymentTransaction.STATUS_SUCCESS,
                paid_at__gte=start_window,
                paid_at__lt=end_window,
            )
            .annotate(month=TruncMonth("paid_at"))
            .values("month")
            .annotate(total=Sum("amount"))
        }
        new_companies_by_month = {
            _month_start(item["month"]): item["count"]
            for item in Company.objects.filter(created_at__lt=end_window)
            .annotate(month=TruncMonth("created_at"))
            .values("month")
            .annotate(count=Count("id"))
        }

        monthly_subscriptions = []
        revenue_line = []
        company_growth = []
        running_company_total = 0
        for months_ago in range(11, -1, -1):
            dt = _add_months(month_start, -months_ago)
            sub_count = subs_by_month.get(dt, 0)
            rev = revenue_by_month.get(dt, 0)
            running_company_total += new_companies_by_month.get(dt, 0)
            month_label = dt.strftime("%b %Y")
            monthly_subscriptions.append({"month": month_label, "count": sub_count})
            revenue_line.append({"month": month_label, "revenue": rev})
            company_growth.append({"month": month_label, "companies": running_company_total})

        revenue_breakdown_qs = (
            PaymentTransaction.objects.filter(status=PaymentTransaction.STATUS_SUCCESS)
            .values("subscription__plan__price")
            .annotate(total=Sum("amount"))
            .order_by("subscription__plan__price")
        )
        plan_breakdown = [
            {
                "plan_price": str(item["subscription__plan__price"] or "0"),
                "revenue": float(item["total"] or 0),
            }
            for item in revenue_breakdown_qs
        ]

        subscription_stats = CompanySubscription.objects.aggregate(
            total=Count("id"),
            churned=Count("id", filter=Q(end_date__lt=now) | Q(is_active=False)),
            trial_total=Count("id", filter=Q(plan__code="trial")),
            paid_total=Count("id", filter=Q(plan__price__gt=0)),
            expired_total=Count("id", filter=Q(end_date__lt=now)),
        )
        total_subscriptions = subscription_stats["total"] or 0
        churned = subscription_stats["churned"] or 0
        trial_total = subscription_stats["trial_total"] or 0
        paid_total = subscription_stats["paid_total"] or 0

        churn_rate = (churned / total_subscriptions * 100) if total_subscriptions else 0
        conversion_rate = (paid_total / trial_total * 100) if trial_total else 0

        pie_distribution = [
            {"label": "Trial", "value": trial_total},
            {"label": "Paid", "value": paid_total},
            {"label": "Expired", "value": subscription_stats["expired_total"] or 0},
        ]

        payload = {
            "mrr": str(mrr),
            "arr": str(arr),
            "new_subscriptions_per_month": monthly_subscriptions,
            "plan_revenue_breakdown": plan_breakdown,
            "churn_rate": round(churn_rate, 2),
            "conversion_rate": round(conversion_rate, 2),
            "revenue_line_chart": revenue_line,
            "subscription_distribution_chart": pie_distribution,
            "company_growth_chart": company_growth,
        }
        cache.set(cache_key, payload, timeout=300)

        return self.success_response(data=payload, message="Analytics loaded.")
