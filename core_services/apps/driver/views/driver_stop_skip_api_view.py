from django.db import transaction
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.company_admin.models import DriverAssignment
from apps.driver.models import DriverRouteRun, DriverRunStop
from apps.driver.views.helpers import (
    ensure_stop_is_current_pending,
    get_driver_for_user,
    get_next_pending_stop,
    get_run_for_driver,
    get_stop_for_run,
)
from apps.core.services.live_tracking import live_tracking_service

from .base import DriverAPIView


class DriverStopSkipSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, allow_blank=False, max_length=500)


class DriverStopSkipAPIView(DriverAPIView):
    @swagger_auto_schema(
        tags=["Driver App"],
        operation_summary="Skip current shop and move to next stop with reason",
        manual_parameters=[
            openapi.Parameter("assignment_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("shop_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
        ],
        request_body=DriverStopSkipSerializer,
        responses={200: "Stop skipped"},
    )
    @transaction.atomic
    def post(self, request, assignment_id, shop_id):
        driver = get_driver_for_user(request.user)
        run = get_run_for_driver(driver, assignment_id)
        stop = get_stop_for_run(run, shop_id)

        serializer = DriverStopSkipSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data["reason"].strip()
        if not reason:
            raise ValidationError({"reason": ["Skip reason is required."]})

        if stop.status == DriverRunStop.STATUS_COMPLETED:
            raise ValidationError({"stop": ["Completed stop cannot be skipped."]})
        if stop.status == DriverRunStop.STATUS_SKIPPED:
            return self.success_response(
                data={
                    "stop_id": stop.id,
                    "skipped_at": stop.skipped_at,
                    "skip_reason": stop.skip_reason,
                },
                message="Stop already skipped.",
            )

        ensure_stop_is_current_pending(run, stop)

        stop.status = DriverRunStop.STATUS_SKIPPED
        stop.skipped_at = timezone.now()
        stop.skip_reason = reason
        stop.save(update_fields=["status", "skipped_at", "skip_reason", "updated_at"])
        live_tracking_service.publish_stop_update(
            company_id=str(run.route.company_id),
            assignment_id=str(run.assignment_id),
            route_run_id=str(run.id),
            stop_id=str(stop.id),
            shop_id=str(stop.shop_id),
            status=stop.status,
            skipped_at=stop.skipped_at,
            skip_reason=stop.skip_reason,
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
                "skipped_at": stop.skipped_at,
                "skip_reason": stop.skip_reason,
                "assignment_completed": assignment_completed,
                "next_shop_id": str(next_stop.shop_id) if next_stop else None,
            },
            message="Stop skipped successfully.",
        )
