from django.db import IntegrityError
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.company_admin.models import Vehicle
from apps.company_admin.serializers import VehicleSerializer

from .base import CompanyAdminAPIView


class VehicleDetailAPIView(CompanyAdminAPIView):
    required_permission_map = {
        "GET": "vehicle.view",
        "PATCH": "vehicle.update",
        "DELETE": "vehicle.delete",
    }
    def _get_vehicle(self, company_id, vehicle_id):
        vehicle = Vehicle.objects.filter(id=vehicle_id, company_id=company_id).only(
            "id",
            "company_id",
            "name",
            "number_plate",
            "status",
            "created_at",
            "updated_at",
        ).first()
        if not vehicle:
            raise NotFound("Vehicle not found.")
        return vehicle

    @swagger_auto_schema(
        tags=["Company Admin"],
        operation_summary="Get vehicle details",
        manual_parameters=[
            openapi.Parameter(
                "vehicle_id",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            )
        ],
        responses={200: "Vehicle loaded", 404: "Vehicle not found"},
    )
    def get(self, request, vehicle_id):
        vehicle = self._get_vehicle(request.user.company_id, vehicle_id)
        return Response(VehicleSerializer(vehicle).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin"],
        operation_summary="Update vehicle",
        manual_parameters=[
            openapi.Parameter(
                "vehicle_id",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            )
        ],
        request_body=VehicleSerializer,
        responses={200: "Vehicle updated", 400: "Validation error", 404: "Vehicle not found"},
    )
    def patch(self, request, vehicle_id):
        vehicle = self._get_vehicle(request.user.company_id, vehicle_id)
        serializer = VehicleSerializer(vehicle, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            updated_vehicle = serializer.save()
        except IntegrityError:
            raise ValidationError({"number_plate": ["A vehicle with this number plate already exists."]})
        payload = VehicleSerializer(updated_vehicle).data
        payload["message"] = "Vehicle updated successfully."
        return Response(payload, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin"],
        operation_summary="Delete vehicle",
        manual_parameters=[
            openapi.Parameter(
                "vehicle_id",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            )
        ],
        responses={200: "Vehicle deleted", 404: "Vehicle not found"},
    )
    def delete(self, request, vehicle_id):
        vehicle = self._get_vehicle(request.user.company_id, vehicle_id)
        vehicle.delete()
        return Response({"message": "Vehicle deleted successfully."}, status=status.HTTP_200_OK)
