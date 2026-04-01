from django.db import IntegrityError, transaction
from django.db.models import F
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.company_admin.models import Route, RouteShop, Shop
from apps.company_admin.serializers import RouteDetailSerializer, RouteShopAddSerializer

from .base import CompanyAdminAPIView


class RouteShopAddAPIView(CompanyAdminAPIView):
    required_permission = "route.update"
    def _get_route(self, company_id, route_id):
        route = Route.objects.filter(company_id=company_id, id=route_id).first()
        if not route:
            raise NotFound("Route not found.")
        return route

    @swagger_auto_schema(
        tags=["Company Admin Routes"],
        operation_summary="Add shop to route",
        manual_parameters=[openapi.Parameter("route_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        request_body=RouteShopAddSerializer,
        responses={200: "Shop added to route"},
    )
    def post(self, request, route_id):
        route = self._get_route(request.user.company_id, route_id)
        serializer = RouteShopAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        shop = Shop.objects.filter(company_id=request.user.company_id, id=payload["shop_id"]).first()
        if not shop:
            raise ValidationError({"shop_id": ["Shop does not belong to this company."]})

        if RouteShop.objects.filter(shop_id=shop.id).exists():
            raise ValidationError({"shop_id": ["Shop is already assigned to a route."]})

        with transaction.atomic():
            current_count = RouteShop.objects.select_for_update().filter(route_id=route.id).count()
            target_position = payload.get("position") or (current_count + 1)
            if target_position > current_count + 1:
                target_position = current_count + 1

            RouteShop.objects.filter(route_id=route.id, position__gte=target_position).update(position=F("position") + 1)

            try:
                RouteShop.objects.create(route_id=route.id, shop_id=shop.id, position=target_position)
            except IntegrityError:
                raise ValidationError({"shop_id": ["Unable to assign shop to route."]})

        route = Route.objects.filter(id=route.id).prefetch_related("route_shops__shop").first()
        payload = RouteDetailSerializer(route, context={"request": request}).data
        payload["message"] = "Shop added to route successfully."
        return Response(payload, status=status.HTTP_200_OK)
