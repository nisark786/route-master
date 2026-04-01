from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.driver.serializers import DriverRouteRunDetailSerializer
from apps.driver.views.helpers import (
    get_assignment_for_driver,
    get_driver_for_user,
    get_or_create_run_for_assignment,
)

from .base import DriverAPIView


class DriverAssignmentStartAPIView(DriverAPIView):
    @swagger_auto_schema(
        tags=["Driver App"],
        operation_summary="Start assigned route execution",
        manual_parameters=[openapi.Parameter("assignment_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        responses={200: "Route already in progress", 201: "Route run started"},
    )
    @transaction.atomic
    def post(self, request, assignment_id):
        driver = get_driver_for_user(request.user)
        assignment = get_assignment_for_driver(driver, assignment_id)
        run, created = get_or_create_run_for_assignment(assignment)

        run = run.__class__.objects.filter(id=run.id).select_related("assignment", "route", "vehicle", "driver").first()
        payload = DriverRouteRunDetailSerializer(run, context={"request": request}).data
        if created:
            return self.success_response(
                data=payload,
                message="Route started successfully.",
                status_code=201,
            )
        return self.success_response(data=payload, message="Route already in progress.")
