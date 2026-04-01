from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.core.services.live_tracking import live_tracking_service
from apps.driver.models import DriverRouteRun, DriverRunStop

from .base import CompanyAdminAPIView


class LiveTrackingVehicleDetailAPIView(CompanyAdminAPIView):
    required_permission = "driver_assignment.view"

    @swagger_auto_schema(
        tags=["Company Admin Live Tracking"],
        operation_summary="Get live tracking detail for in-progress vehicle route",
        manual_parameters=[
            openapi.Parameter("vehicle_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter(
                "history_limit",
                openapi.IN_QUERY,
                type=openapi.TYPE_INTEGER,
                required=False,
                description="Maximum number of route-history points to return (default 500, max 2000).",
            ),
        ],
        responses={200: "Live tracking detail loaded"},
    )
    def get(self, request, vehicle_id):
        try:
            history_limit = int(request.query_params.get("history_limit") or 500)
        except (TypeError, ValueError):
            history_limit = 500

        run = (
            DriverRouteRun.objects.filter(
                route__company_id=request.user.company_id,
                vehicle_id=vehicle_id,
                status=DriverRouteRun.STATUS_IN_PROGRESS,
            )
            .select_related("assignment", "route", "vehicle", "driver")
            .first()
        )
        if not run:
            raise NotFound("No in-progress route found for this vehicle.")

        stops = list(run.stops.select_related("shop").order_by("position"))
        all_shops = [
            {
                "shop_id": str(item.shop_id),
                "name": item.shop.name,
                "position": item.position,
                "status": item.status,
                "latitude": float(item.shop.latitude) if item.shop.latitude is not None else None,
                "longitude": float(item.shop.longitude) if item.shop.longitude is not None else None,
                "location_display_name": item.shop.location_display_name,
                "completed_at": item.check_out_at,
                "skipped_at": item.skipped_at,
            }
            for item in stops
        ]
        completed_or_skipped = [item for item in all_shops if item["status"] in {DriverRunStop.STATUS_COMPLETED, DriverRunStop.STATUS_SKIPPED}]

        history = live_tracking_service.get_history_for_assignment(
            company_id=str(request.user.company_id),
            assignment_id=str(run.assignment_id),
            limit=history_limit,
        )

        return Response(
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
                "latest_location": live_tracking_service.get_latest_for_assignment(
                    company_id=str(request.user.company_id),
                    assignment_id=str(run.assignment_id),
                ),
                "route_history": history,
                "shops": all_shops,
                "completed_or_skipped_shops": completed_or_skipped,
            },
            status=status.HTTP_200_OK,
        )
