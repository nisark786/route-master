from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.driver.serializers import DriverRouteRunDetailSerializer
from apps.driver.views.helpers import get_driver_for_user, get_run_for_driver

from .base import DriverAPIView


class DriverAssignmentDetailAPIView(DriverAPIView):
    @swagger_auto_schema(
        tags=["Driver App"],
        operation_summary="Get started route execution details",
        manual_parameters=[openapi.Parameter("assignment_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        responses={200: "Run details loaded"},
    )
    def get(self, request, assignment_id):
        driver = get_driver_for_user(request.user)
        run = get_run_for_driver(driver, assignment_id)
        payload = DriverRouteRunDetailSerializer(run, context={"request": request}).data
        return self.success_response(data=payload, message="Route details loaded.")
