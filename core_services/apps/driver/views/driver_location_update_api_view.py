from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError

from apps.driver.models import DriverRouteRun
from apps.driver.serializers import DriverLocationUpdateSerializer
from apps.driver.views.helpers import get_assignment_for_driver, get_driver_for_user, get_run_for_driver
from apps.core.services.live_tracking import live_tracking_service

from .base import DriverAPIView


class DriverLocationUpdateAPIView(DriverAPIView):
    @swagger_auto_schema(
        tags=["Driver App"],
        operation_summary="Update live location for active assignment",
        manual_parameters=[openapi.Parameter("assignment_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        request_body=DriverLocationUpdateSerializer,
        responses={200: "Location updated"},
    )
    def post(self, request, assignment_id):
        serializer = DriverLocationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        driver = get_driver_for_user(request.user)
        assignment = get_assignment_for_driver(driver, assignment_id)
        run = get_run_for_driver(driver, assignment_id)
        if run.status != DriverRouteRun.STATUS_IN_PROGRESS:
            raise ValidationError({"assignment": ["Live tracking is only available for in-progress assignments."]})

        location = live_tracking_service.update_location(
            company_id=str(request.user.company_id),
            assignment_id=str(assignment.id),
            route_run_id=str(run.id),
            vehicle_id=str(assignment.vehicle_id),
            driver_id=str(driver.id),
            latitude=serializer.validated_data["latitude"],
            longitude=serializer.validated_data["longitude"],
            speed_kph=serializer.validated_data.get("speed_kph", 0),
            heading=serializer.validated_data.get("heading", 0),
            captured_at=serializer.validated_data.get("captured_at"),
        )
        return self.success_response(data=location, message="Location updated.")
