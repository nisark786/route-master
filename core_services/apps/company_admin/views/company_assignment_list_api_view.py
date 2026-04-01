from django.core.cache import cache
from django.db import models
from django.db.models import Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from apps.company_admin.models import DriverAssignment
from apps.company_admin.serializers import AssignmentListQuerySerializer
from apps.company_admin.services.cache import company_collection_cache_key

from .base import CompanyAdminAPIView


class CompanyAssignmentListAPIView(CompanyAdminAPIView):
    required_permission = "driver_assignment.view"
    @swagger_auto_schema(
        tags=["Company Admin Drivers"],
        operation_summary="Company schedule assignments",
        manual_parameters=[
            openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                enum=["all", "ASSIGNED", "IN_ROUTE", "COMPLETED", "CANCELLED"],
            ),
        ],
        responses={200: "Assignments loaded"},
    )
    def get(self, request):
        query_serializer = AssignmentListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        query = query_serializer.validated_data
        search = query["search"].strip()
        cache_key = company_collection_cache_key(
            request.user.company_id,
            "assignments",
            query["status"],
            search or "all",
        )
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        assignments = (
            DriverAssignment.objects.filter(driver__user__company_id=request.user.company_id)
            .values(
                "id",
                "scheduled_at",
                "status",
                "notes",
                "created_at",
                "updated_at",
                "driver",
                "route",
                "vehicle",
                driver_name=models.F("driver__name"),
                driver_mobile_number=models.F("driver__user__mobile_number"),
                route_name=models.F("route__route_name"),
                vehicle_name=models.F("vehicle__name"),
                vehicle_number_plate=models.F("vehicle__number_plate"),
            )
            .order_by("-scheduled_at", "-created_at")
        )

        if query["status"] != "all":
            assignments = assignments.filter(status=query["status"])

        if search:
            assignments = assignments.filter(
                Q(driver__name__icontains=search)
                | Q(driver__user__mobile_number__icontains=search)
                | Q(route__route_name__icontains=search)
                | Q(vehicle__name__icontains=search)
                | Q(vehicle__number_plate__icontains=search)
            )

        payload = [
            {
                **item,
                "id": str(item["id"]),
                "driver": str(item["driver"]),
                "route": str(item["route"]) if item.get("route") else None,
                "vehicle": str(item["vehicle"]) if item.get("vehicle") else None,
            }
            for item in assignments
        ]
        cache.set(cache_key, payload, timeout=90)
        return Response(payload, status=status.HTTP_200_OK)
