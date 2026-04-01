from django.core.cache import cache
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from apps.company_admin.services.cache import company_collection_cache_key
from apps.core.services.live_tracking import live_tracking_service
from apps.driver.models import DriverRouteRun

from .base import CompanyAdminAPIView


class LiveTrackingVehicleListAPIView(CompanyAdminAPIView):
    required_permission = "driver_assignment.view"

    @swagger_auto_schema(
        tags=["Company Admin Live Tracking"],
        operation_summary="List vehicles with in-progress routes and latest live location",
        responses={200: "Live vehicles loaded"},
    )
    def get(self, request):
        cache_key = company_collection_cache_key(request.user.company_id, "live-tracking-vehicles")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        runs = (
            DriverRouteRun.objects.filter(
                route__company_id=request.user.company_id,
                status=DriverRouteRun.STATUS_IN_PROGRESS,
            )
            .select_related("assignment", "route", "vehicle", "driver")
            .only(
                "id",
                "assignment_id",
                "vehicle_id",
                "vehicle__name",
                "vehicle__number_plate",
                "driver_id",
                "driver__name",
                "route_id",
                "route__route_name",
                "started_at",
            )
            .order_by("-started_at")
        )
        latest_by_assignment = live_tracking_service.get_latest_for_assignments(
            company_id=str(request.user.company_id),
            assignment_ids=[str(run.assignment_id) for run in runs],
        )

        data = []
        for run in runs:
            latest = latest_by_assignment.get(str(run.assignment_id))
            data.append(
                {
                    "company_id": str(request.user.company_id),
                    "run_id": str(run.id),
                    "assignment_id": str(run.assignment_id),
                    "vehicle_id": str(run.vehicle_id),
                    "vehicle_name": run.vehicle.name,
                    "vehicle_number_plate": run.vehicle.number_plate,
                    "driver_id": str(run.driver_id),
                    "driver_name": run.driver.name,
                    "route_id": str(run.route_id),
                    "route_name": run.route.route_name,
                    "started_at": run.started_at,
                    "latest_location": latest,
                }
            )
        cache.set(cache_key, data, timeout=10)
        return Response(data, status=status.HTTP_200_OK)
