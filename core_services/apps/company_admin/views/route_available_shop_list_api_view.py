from django.core.cache import cache
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from apps.company_admin.models import Shop
from apps.company_admin.services.cache import company_collection_cache_key

from .base import CompanyAdminAPIView


class RouteAvailableShopListAPIView(CompanyAdminAPIView):
    required_permission = "route.view"
    @swagger_auto_schema(
        tags=["Company Admin Routes"],
        operation_summary="List unassigned shops",
        responses={200: "Unassigned shops loaded"},
    )
    def get(self, request):
        cache_key = company_collection_cache_key(request.user.company_id, "route-available-shops")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        payload = [
            {
                **item,
                "id": str(item["id"]),
            }
            for item in (
            Shop.objects.filter(company_id=request.user.company_id, route_assignments__isnull=True)
            .values("id", "name", "owner_name")
            .order_by("name")
            )
        ]
        cache.set(cache_key, payload, timeout=120)
        return Response(payload, status=status.HTTP_200_OK)
