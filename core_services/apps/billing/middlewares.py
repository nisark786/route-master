from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db.models import F
from django.http import JsonResponse
from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from apps.billing.models import CompanySubscription
from apps.company.models import Company


class SubscriptionAccessMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not getattr(settings, "ENFORCE_SUBSCRIPTION_ACCESS", True):
            return None

        if self._is_exempt_path(request.path):
            return None

        company_id = getattr(request, "company_id", None)
        if not company_id:
            return None

        state = self._get_company_subscription_state(company_id)
        if not state["company_exists"]:
            return JsonResponse(
                {"message": "Company profile not found.", "code": "COMPANY_NOT_FOUND"},
                status=403,
            )
        if state["company_suspended"]:
            return JsonResponse(
                {
                    "message": "Company access is suspended. Contact support or renew subscription.",
                    "code": "COMPANY_SUSPENDED",
                },
                status=403,
            )
        if not state["subscription_valid"]:
            return JsonResponse(
                {
                    "message": "Subscription expired. Please renew to continue.",
                    "code": "SUBSCRIPTION_EXPIRED",
                },
                status=403,
            )
        return None

    def _is_exempt_path(self, path):
        exempt_prefixes = getattr(
            settings,
            "SUBSCRIPTION_EXEMPT_PATH_PREFIXES",
            [
                "/admin/",
                "/swagger/",
                "/redoc/",
                "/api/auth/",
                "/api/billing/",
                "/healthz/",
                "/metrics",
            ],
        )
        return any(path.startswith(prefix) for prefix in exempt_prefixes)

    def _get_company_subscription_state(self, company_id):
        cache_key = f"billing:company-subscription-state:{company_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        now = timezone.now()
        CompanySubscription.objects.filter(
            company_id=company_id,
            pending_plan__isnull=False,
            pending_plan_effective_at__lte=now,
        ).update(
            plan=F("pending_plan"),
            pending_plan=None,
            pending_plan_effective_at=None,
        )
        grace_days = max(int(getattr(settings, "SUBSCRIPTION_GRACE_DAYS", 0)), 0)
        grace_delta = timedelta(days=grace_days)

        company = Company.objects.filter(id=company_id).values("is_active", "operational_status").first()
        subscription = (
            CompanySubscription.objects.filter(company_id=company_id)
            .values("is_active", "end_date")
            .first()
        )

        state = {
            "company_exists": bool(company),
            "company_suspended": True,
            "subscription_valid": False,
        }
        if company:
            state["company_suspended"] = (
                company["operational_status"] == Company.STATUS_SUSPENDED or not company["is_active"]
            )
        if subscription:
            effective_expiry = subscription["end_date"] + grace_delta
            state["subscription_valid"] = bool(subscription["is_active"] and effective_expiry >= now)

        cache.set(
            cache_key,
            state,
            timeout=max(int(getattr(settings, "SUBSCRIPTION_STATE_CACHE_SECONDS", 60)), 10),
        )
        return state
