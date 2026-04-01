from django.db import transaction
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError

from apps.driver.models import DriverRunStop
from apps.driver.views.helpers import (
    ensure_stop_is_current_pending,
    get_driver_for_user,
    get_run_for_driver,
    get_stop_for_run,
)
from apps.core.services.live_tracking import live_tracking_service

from .base import DriverAPIView


class DriverStopCheckInAPIView(DriverAPIView):
    @swagger_auto_schema(
        tags=["Driver App"],
        operation_summary="Check in at a shop stop",
        manual_parameters=[
            openapi.Parameter("assignment_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("shop_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
        ],
        responses={200: "Checked in"},
    )
    @transaction.atomic
    def post(self, request, assignment_id, shop_id):
        driver = get_driver_for_user(request.user)
        run = get_run_for_driver(driver, assignment_id)
        stop = get_stop_for_run(run, shop_id)

        if stop.status == DriverRunStop.STATUS_COMPLETED:
            raise ValidationError({"stop": ["This stop is already completed."]})
        if stop.status == DriverRunStop.STATUS_CHECKED_IN:
            return self.success_response(
                data={"stop_id": stop.id, "check_in_at": stop.check_in_at},
                message="Already checked in for this stop.",
            )

        ensure_stop_is_current_pending(run, stop)
        stop.status = DriverRunStop.STATUS_CHECKED_IN
        stop.check_in_at = timezone.now()
        stop.save(update_fields=["status", "check_in_at", "updated_at"])
        live_tracking_service.publish_stop_update(
            company_id=str(run.route.company_id),
            assignment_id=str(run.assignment_id),
            route_run_id=str(run.id),
            stop_id=str(stop.id),
            shop_id=str(stop.shop_id),
            status=stop.status,
            check_in_at=stop.check_in_at,
        )

        return self.success_response(
            data={"stop_id": stop.id, "check_in_at": stop.check_in_at},
            message="Checked in successfully.",
        )
