from django.db import IntegrityError
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.company_admin.models import Driver, DriverAssignment, Route, Vehicle
from apps.company_admin.serializers import DriverAssignmentSerializer

from .base import CompanyAdminAPIView


class DriverAssignmentListCreateAPIView(CompanyAdminAPIView):
    required_permission_map = {
        "GET": "driver_assignment.view",
        "POST": "driver_assignment.create",
    }
    def _get_driver(self, company_id, driver_id):
        driver = Driver.objects.filter(user__company_id=company_id, id=driver_id).first()
        if not driver:
            raise NotFound("Driver not found.")
        return driver

    @swagger_auto_schema(
        tags=["Company Admin Drivers"],
        operation_summary="List driver assignments",
        manual_parameters=[openapi.Parameter("driver_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        responses={200: "Assignments loaded"},
    )
    def get(self, request, driver_id):
        driver = self._get_driver(request.user.company_id, driver_id)
        assignments = (
            DriverAssignment.objects.filter(driver_id=driver.id)
            .select_related("driver__user", "route", "vehicle")
            .order_by("-scheduled_at", "-created_at")
        )
        return Response(DriverAssignmentSerializer(assignments, many=True).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin Drivers"],
        operation_summary="Create driver assignment",
        manual_parameters=[openapi.Parameter("driver_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        request_body=DriverAssignmentSerializer,
        responses={201: "Assignment created"},
    )
    def post(self, request, driver_id):
        driver = self._get_driver(request.user.company_id, driver_id)
        if "status" in request.data:
            provided_status = str(request.data.get("status") or "").strip().upper()
            if provided_status and provided_status != DriverAssignment.STATUS_ASSIGNED:
                raise ValidationError({"status": ["Status is system-managed and cannot be set manually."]})
        serializer = DriverAssignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        route = Route.objects.filter(company_id=request.user.company_id, id=payload["route"].id).first()
        if not route:
            raise ValidationError({"route": ["Route not found in this company."]})

        vehicle = Vehicle.objects.filter(company_id=request.user.company_id, id=payload["vehicle"].id).first()
        if not vehicle:
            raise ValidationError({"vehicle": ["Vehicle not found in this company."]})

        try:
            assignment = DriverAssignment.objects.create(
                driver=driver,
                route=route,
                vehicle=vehicle,
                scheduled_at=payload["scheduled_at"],
                status=DriverAssignment.STATUS_ASSIGNED,
                notes=payload.get("notes", ""),
            )
        except IntegrityError:
            # Idempotent behavior for Copilot/automatic approvals:
            # if the exact assignment already exists, return it instead of failing.
            existing = (
                DriverAssignment.objects.filter(driver=driver, scheduled_at=payload["scheduled_at"])
                .select_related("driver__user", "route", "vehicle")
                .first()
            )
            if existing and existing.route_id == route.id and existing.vehicle_id == vehicle.id:
                existing_payload = DriverAssignmentSerializer(existing).data
                existing_payload["message"] = "Driver assignment already exists for this date/time."
                return Response(existing_payload, status=status.HTTP_200_OK)

            conflict_driver = (
                DriverAssignment.objects.filter(driver=driver, scheduled_at=payload["scheduled_at"])
                .select_related("route", "vehicle")
                .first()
            )
            if conflict_driver:
                raise ValidationError(
                    {
                        "scheduled_at": [
                            f"Driver already has assignment {conflict_driver.id} at this date/time."
                        ]
                    }
                )

            conflict_vehicle = (
                DriverAssignment.objects.filter(vehicle=vehicle, scheduled_at=payload["scheduled_at"])
                .select_related("driver")
                .first()
            )
            if conflict_vehicle:
                raise ValidationError(
                    {
                        "scheduled_at": [
                            f"Vehicle already has assignment {conflict_vehicle.id} at this date/time."
                        ]
                    }
                )
            raise ValidationError(
                {"scheduled_at": ["Driver or vehicle already has an assignment at this date/time."]}
            )

        assignment = DriverAssignment.objects.select_related("driver__user", "route", "vehicle").get(id=assignment.id)
        payload = DriverAssignmentSerializer(assignment).data
        payload["message"] = "Driver assignment created successfully."
        return Response(payload, status=status.HTTP_201_CREATED)
