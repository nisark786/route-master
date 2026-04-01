from django.db import transaction
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError

from apps.company_admin.models import DriverAssignment
from apps.driver.models import DriverRouteRun, DriverRunStop
from apps.driver.views.helpers import (
    get_driver_for_user,
    get_next_pending_stop,
    get_run_for_driver,
    get_stop_for_run,
)
from apps.core.services.live_tracking import live_tracking_service

from .base import DriverAPIView


class DriverStopCheckOutAPIView(DriverAPIView):
    @swagger_auto_schema(
        tags=["Driver App"],
        operation_summary="Check out from a shop and move to next stop",
        manual_parameters=[
            openapi.Parameter("assignment_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("shop_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
        ],
        responses={200: "Checked out"},
    )
    @transaction.atomic
    def post(self, request, assignment_id, shop_id):
        driver = get_driver_for_user(request.user)
        run = get_run_for_driver(driver, assignment_id)
        stop = get_stop_for_run(run, shop_id)

        if stop.status == DriverRunStop.STATUS_COMPLETED:
            return self.success_response(
                data={"stop_id": stop.id, "check_out_at": stop.check_out_at},
                message="Stop already checked out.",
            )
        if stop.status != DriverRunStop.STATUS_CHECKED_IN:
            raise ValidationError({"stop": ["Check in before check out."]})
        if not stop.invoice_number:
            raise ValidationError({"stop": ["Complete order and generate invoice before check out."]})

        stop.status = DriverRunStop.STATUS_COMPLETED
        stop.check_out_at = timezone.now()
        stop.save(update_fields=["status", "check_out_at", "updated_at"])
        live_tracking_service.publish_stop_update(
            company_id=str(run.route.company_id),
            assignment_id=str(run.assignment_id),
            route_run_id=str(run.id),
            stop_id=str(stop.id),
            shop_id=str(stop.shop_id),
            status=stop.status,
            check_out_at=stop.check_out_at,
        )

        next_stop = get_next_pending_stop(run)
        assignment_completed = next_stop is None

        if assignment_completed:
            run.status = DriverRouteRun.STATUS_COMPLETED
            run.completed_at = timezone.now()
            run.save(update_fields=["status", "completed_at", "updated_at"])

            assignment = run.assignment
            assignment.status = DriverAssignment.STATUS_COMPLETED
            assignment.save(update_fields=["status", "updated_at"])

            driver.status = "AVAILABLE"
            driver.save(update_fields=["status", "updated_at"])

        return self.success_response(
            data={
                "stop_id": stop.id,
                "check_out_at": stop.check_out_at,
                "assignment_completed": assignment_completed,
                "next_shop_id": str(next_stop.shop_id) if next_stop else None,
            },
            message="Checked out successfully.",
        )
