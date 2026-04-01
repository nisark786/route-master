from django.db import IntegrityError
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.company_admin.models import Driver, DriverAssignment, Route, Vehicle
from apps.company_admin.serializers import DriverAssignmentSerializer

from .base import CompanyAdminAPIView


class DriverAssignmentDetailAPIView(CompanyAdminAPIView):
    required_permission_map = {
        "PATCH": "driver_assignment.update",
        "DELETE": "driver_assignment.delete",
    }
    def _get_driver(self, company_id, driver_id):
        driver = Driver.objects.filter(user__company_id=company_id, id=driver_id).first()
        if not driver:
            raise NotFound("Driver not found.")
        return driver

    def _get_assignment(self, driver_id, assignment_id):
        assignment = (
            DriverAssignment.objects.filter(driver_id=driver_id, id=assignment_id)
            .select_related("driver__user", "route", "vehicle")
            .first()
        )
        if not assignment:
            raise NotFound("Driver assignment not found.")
        return assignment

    @swagger_auto_schema(
        tags=["Company Admin Drivers"],
        operation_summary="Update driver assignment",
        manual_parameters=[
            openapi.Parameter("driver_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("assignment_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
        ],
        request_body=DriverAssignmentSerializer,
        responses={200: "Assignment updated"},
    )
    def patch(self, request, driver_id, assignment_id):
        driver = self._get_driver(request.user.company_id, driver_id)
        assignment = self._get_assignment(driver.id, assignment_id)
        if assignment.status != DriverAssignment.STATUS_ASSIGNED:
            raise ValidationError({"assignment": ["Only ASSIGNED assignments can be edited."]})
        if "status" in request.data:
            raise ValidationError({"status": ["Status is system-managed and cannot be edited manually."]})

        serializer = DriverAssignmentSerializer(assignment, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        if "route" in payload:
            route = Route.objects.filter(company_id=request.user.company_id, id=payload["route"].id).first()
            if not route:
                raise ValidationError({"route": ["Route not found in this company."]})
            assignment.route = route

        if "vehicle" in payload:
            vehicle = Vehicle.objects.filter(company_id=request.user.company_id, id=payload["vehicle"].id).first()
            if not vehicle:
                raise ValidationError({"vehicle": ["Vehicle not found in this company."]})
            assignment.vehicle = vehicle

        if "scheduled_at" in payload:
            assignment.scheduled_at = payload["scheduled_at"]
        if "notes" in payload:
            assignment.notes = payload["notes"]

        try:
            assignment.save()
        except IntegrityError:
            raise ValidationError(
                {"scheduled_at": ["Driver or vehicle already has an assignment at this date/time."]}
            )

        refreshed = DriverAssignment.objects.select_related("driver__user", "route", "vehicle").get(id=assignment.id)
        payload = DriverAssignmentSerializer(refreshed).data
        payload["message"] = "Driver assignment updated successfully."
        return Response(payload, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin Drivers"],
        operation_summary="Delete driver assignment",
        manual_parameters=[
            openapi.Parameter("driver_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("assignment_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
        ],
        responses={204: "Deleted"},
    )
    def delete(self, request, driver_id, assignment_id):
        driver = self._get_driver(request.user.company_id, driver_id)
        assignment = self._get_assignment(driver.id, assignment_id)
        if assignment.status != DriverAssignment.STATUS_ASSIGNED:
            raise ValidationError({"assignment": ["Only ASSIGNED assignments can be deleted."]})
        assignment.delete()
        return Response({"message": "Driver assignment deleted successfully."}, status=status.HTTP_200_OK)
