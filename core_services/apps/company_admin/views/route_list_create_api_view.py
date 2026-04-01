from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.company_admin.models import Route, RouteShop, Shop
from apps.company_admin.serializers import RouteCreateSerializer, RouteDetailSerializer, RouteListQuerySerializer
from apps.company_admin.services.cache import company_collection_cache_key

from .base import CompanyAdminAPIView


class RouteListCreateAPIView(CompanyAdminAPIView):
    required_permission_map = {
        "GET": "route.view",
        "POST": "route.create",
    }
    @swagger_auto_schema(
        tags=["Company Admin Routes"],
        operation_summary="List routes",
        manual_parameters=[openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING)],
        responses={200: "Routes loaded"},
    )
    def get(self, request):
        query_serializer = RouteListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        search = query_serializer.validated_data["search"].strip()
        cache_key = company_collection_cache_key(request.user.company_id, "routes", search or "all")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        payload = [
            {
                **item,
                "id": str(item["id"]),
            }
            for item in (
            Route.objects.filter(company_id=request.user.company_id)
            .annotate(shops_count=Count("route_shops"))
            .values("id", "route_name", "start_point", "end_point", "shops_count", "created_at", "updated_at")
            .order_by("-created_at")
            )
        ]
        if search:
            payload = [
                {
                    **item,
                    "id": str(item["id"]),
                }
                for item in (
                Route.objects.filter(company_id=request.user.company_id)
                .filter(
                Q(route_name__icontains=search) | Q(start_point__icontains=search) | Q(end_point__icontains=search)
                )
                .annotate(shops_count=Count("route_shops"))
                .values("id", "route_name", "start_point", "end_point", "shops_count", "created_at", "updated_at")
                .order_by("-created_at")
                )
            ]
        cache.set(cache_key, payload, timeout=120)
        return Response(payload, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin Routes"],
        operation_summary="Create route",
        request_body=RouteCreateSerializer,
        responses={201: "Route created"},
    )
    def post(self, request):
        serializer = RouteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        requested_shops = payload.get("shops", [])

        shop_ids = [item["shop_id"] for item in requested_shops]
        if len(shop_ids) != len(set(shop_ids)):
            raise ValidationError({"shops": ["Duplicate shop entries are not allowed."]})

        company_shop_ids = set(
            Shop.objects.filter(company_id=request.user.company_id, id__in=shop_ids).values_list("id", flat=True)
        )
        missing_shop_ids = [str(shop_id) for shop_id in shop_ids if shop_id not in company_shop_ids]
        if missing_shop_ids:
            raise ValidationError({"shops": [f"Invalid shops for company: {', '.join(missing_shop_ids)}"]})

        already_assigned = set(RouteShop.objects.filter(shop_id__in=shop_ids).values_list("shop_id", flat=True))
        if already_assigned:
            raise ValidationError({"shops": ["One or more selected shops are already assigned to another route."]})

        with transaction.atomic():
            try:
                route = Route.objects.create(
                    company_id=request.user.company_id,
                    route_name=payload["route_name"],
                    start_point=payload["start_point"],
                    end_point=payload["end_point"],
                )
            except IntegrityError:
                raise ValidationError({"route_name": ["A route with this name already exists."]})

            ordered_shop_ids = []
            for item in requested_shops:
                position = item.get("position")
                if position is None or position > len(ordered_shop_ids) + 1:
                    ordered_shop_ids.append(item["shop_id"])
                else:
                    ordered_shop_ids.insert(position - 1, item["shop_id"])

            RouteShop.objects.bulk_create(
                [
                    RouteShop(route=route, shop_id=shop_id, position=index + 1)
                    for index, shop_id in enumerate(ordered_shop_ids)
                ]
            )

        route = Route.objects.filter(id=route.id).prefetch_related("route_shops__shop").first()
        payload = RouteDetailSerializer(route, context={"request": request}).data
        payload["message"] = "Route created successfully."
        return Response(payload, status=status.HTTP_201_CREATED)
