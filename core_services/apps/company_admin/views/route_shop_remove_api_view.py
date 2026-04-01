from django.db import transaction
from django.db.models import F
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.company_admin.models import Route, RouteShop
from apps.company_admin.serializers import RouteDetailSerializer

from .base import CompanyAdminAPIView


class RouteShopRemoveAPIView(CompanyAdminAPIView):
    required_permission = "route.update"
    def _get_route(self, company_id, route_id):
        route = Route.objects.filter(company_id=company_id, id=route_id).first()
        if not route:
            raise NotFound("Route not found.")
        return route

    @swagger_auto_schema(
        tags=["Company Admin Routes"],
        operation_summary="Remove shop from route",
        manual_parameters=[
            openapi.Parameter("route_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("shop_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
        ],
        responses={200: "Shop removed from route"},
    )
    def delete(self, request, route_id, shop_id):
        route = self._get_route(request.user.company_id, route_id)

        with transaction.atomic():
            assignment = RouteShop.objects.select_for_update().filter(route_id=route.id, shop_id=shop_id).first()
            if not assignment:
                raise NotFound("Shop assignment not found in route.")

            removed_position = assignment.position
            assignment.delete()
            RouteShop.objects.filter(route_id=route.id, position__gt=removed_position).update(position=F("position") - 1)

        refreshed = Route.objects.filter(id=route.id).prefetch_related("route_shops__shop").first()
        payload = RouteDetailSerializer(refreshed, context={"request": request}).data
        payload["message"] = "Shop removed from route successfully."
        return Response(payload, status=status.HTTP_200_OK)
