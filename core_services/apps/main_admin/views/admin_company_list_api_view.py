import hashlib

from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.main_admin.serializers import CompanyListQuerySerializer
from apps.billing.models import CompanySubscription
from apps.company.models import Company

from .base import SuperAdminAPIView


class AdminCompanyListAPIView(SuperAdminAPIView):
    @swagger_auto_schema(
        tags=["Main Admin"],
        operation_summary="List companies",
        operation_description="Paginated company list with search and status filters.",
        manual_parameters=[
            openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                enum=["all", "trial", "active", "expired", "suspended"],
            ),
            openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("page_size", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ],
        responses={200: "Paginated company list", 401: "Unauthorized", 403: "Forbidden"},
    )
    def get(self, request):
        serializer = CompanyListQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data

        cache_key = "main_admin:companies:" + hashlib.md5(
            f"{query['search']}|{query['status']}|{query['page']}|{query['page_size']}".encode("utf-8")
        ).hexdigest()
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return self.success_response(data=cached_payload, message="Companies loaded.")

        companies = (
            Company.objects.select_related("companysubscription__plan")
            .annotate(
                drivers_count=Count("user", filter=Q(user__role="DRIVER"), distinct=True),
                shops_count=Count("user", filter=Q(user__role="SHOP_OWNER"), distinct=True),
            )
            .order_by("-created_at")
        )
        search = query["search"].strip()
        if search:
            companies = companies.filter(Q(name__icontains=search) | Q(official_email__icontains=search))

        status_filter = query["status"]
        now = timezone.now()
        if status_filter == "suspended":
            companies = companies.filter(operational_status=Company.STATUS_SUSPENDED)
        elif status_filter == "trial":
            companies = companies.filter(companysubscription__plan__code="trial")
        elif status_filter == "active":
            companies = companies.filter(
                companysubscription__end_date__gte=now,
                companysubscription__is_active=True,
                operational_status=Company.STATUS_ACTIVE,
            )
        elif status_filter == "expired":
            companies = companies.filter(companysubscription__end_date__lt=now)

        paginator = Paginator(companies, query["page_size"])
        page_obj = paginator.get_page(query["page"])
        page_companies = list(page_obj.object_list)

        data = []
        for company in page_companies:
            try:
                subscription = company.companysubscription
            except CompanySubscription.DoesNotExist:
                subscription = None
            data.append(
                {
                    "id": str(company.id),
                    "name": company.name,
                    "official_email": company.official_email,
                    "operational_status": company.operational_status,
                    "subscription_status": (
                        "EXPIRED" if subscription and subscription.end_date < now else "ACTIVE" if subscription else "NONE"
                    ),
                    "plan_name": subscription.plan.name if subscription else None,
                    "drivers_count": company.drivers_count,
                    "shops_count": company.shops_count,
                    "created_at": company.created_at,
                }
            )

        payload = {"count": paginator.count, "page": page_obj.number, "page_size": query["page_size"], "results": data}
        cache.set(cache_key, payload, timeout=120)

        return self.success_response(data=payload, message="Companies loaded.")
