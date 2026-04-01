from django.db import transaction
from django.db.models import F
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.company_admin.models import Route, RouteShop
from apps.company_admin.serializers import RouteDetailSerializer, RouteShopPositionUpdateSerializer

from .base import CompanyAdminAPIView


class RouteShopPositionUpdateAPIView(CompanyAdminAPIView):
    required_permission = "route.update"
    def _get_route(self, company_id, route_id):
        route = Route.objects.filter(company_id=company_id, id=route_id).first()
        if not route:
            raise NotFound("Route not found.")
        return route

    @swagger_auto_schema(
        tags=["Company Admin Routes"],
        operation_summary="Move shop position in route",
        manual_parameters=[
            openapi.Parameter("route_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("shop_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
        ],
        request_body=RouteShopPositionUpdateSerializer,
        responses={200: "Shop position updated"},
    )
    def patch(self, request, route_id, shop_id):
        route = self._get_route(request.user.company_id, route_id)
        serializer = RouteShopPositionUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_position = serializer.validated_data["position"]

        with transaction.atomic():
            assignment = RouteShop.objects.select_for_update().filter(route_id=route.id, shop_id=shop_id).first()
            if not assignment:
                raise NotFound("Shop assignment not found in route.")

            current_count = RouteShop.objects.select_for_update().filter(route_id=route.id).count()
            if requested_position > current_count:
                requested_position = current_count

            current_position = assignment.position
            if requested_position == current_position:
                refreshed = Route.objects.filter(id=route.id).prefetch_related("route_shops__shop").first()
                payload = RouteDetailSerializer(refreshed, context={"request": request}).data
                payload["message"] = "Shop position updated successfully."
                return Response(payload, status=status.HTTP_200_OK)

            if requested_position < current_position:
                RouteShop.objects.filter(
                    route_id=route.id,
                    position__gte=requested_position,
                    position__lt=current_position,
                ).exclude(id=assignment.id).update(position=F("position") + 1)
            else:
                RouteShop.objects.filter(
                    route_id=route.id,
                    position__gt=current_position,
                    position__lte=requested_position,
                ).exclude(id=assignment.id).update(position=F("position") - 1)

            assignment.position = requested_position
            assignment.save(update_fields=["position", "updated_at"])

        refreshed = Route.objects.filter(id=route.id).prefetch_related("route_shops__shop").first()
        payload = RouteDetailSerializer(refreshed, context={"request": request}).data
        payload["message"] = "Shop position updated successfully."
        return Response(payload, status=status.HTTP_200_OK)
