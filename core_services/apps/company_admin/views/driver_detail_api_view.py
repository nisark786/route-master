from django.db import IntegrityError
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.company_admin.models import Driver
from apps.company_admin.serializers import DriverSerializer

from .base import CompanyAdminAPIView


class DriverDetailAPIView(CompanyAdminAPIView):
    required_permission_map = {
        "GET": "driver.view",
        "PATCH": "driver.update",
        "DELETE": "driver.delete",
    }
    def _get_driver(self, company_id, driver_id):
        driver = (
            Driver.objects.filter(user__company_id=company_id, id=driver_id)
            .select_related("user")
            .only(
                "id",
                "name",
                "age",
                "status",
                "created_at",
                "updated_at",
                "user__id",
                "user__mobile_number",
            )
            .first()
        )
        if not driver:
            raise NotFound("Driver not found.")
        return driver

    @swagger_auto_schema(
        tags=["Company Admin Drivers"],
        operation_summary="Driver detail",
        manual_parameters=[openapi.Parameter("driver_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        responses={200: "Driver loaded"},
    )
    def get(self, request, driver_id):
        driver = self._get_driver(request.user.company_id, driver_id)
        return Response(DriverSerializer(driver).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin Drivers"],
        operation_summary="Update driver",
        manual_parameters=[openapi.Parameter("driver_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        request_body=DriverSerializer,
        responses={200: "Driver updated"},
    )
    def patch(self, request, driver_id):
        driver = self._get_driver(request.user.company_id, driver_id)
        serializer = DriverSerializer(driver, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            updated_driver = serializer.save()
            if "user" in serializer.validated_data and "mobile_number" in serializer.validated_data["user"]:
                updated_driver.user.mobile_number = serializer.validated_data["user"]["mobile_number"]
                updated_driver.user.save(update_fields=["mobile_number"])
        except IntegrityError:
            raise ValidationError({"mobile_number": ["A driver with this mobile number already exists."]})
        payload = DriverSerializer(updated_driver).data
        payload["message"] = "Driver updated successfully."
        return Response(payload, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin Drivers"],
        operation_summary="Delete driver",
        manual_parameters=[openapi.Parameter("driver_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        responses={204: "Deleted"},
    )
    def delete(self, request, driver_id):
        driver = self._get_driver(request.user.company_id, driver_id)
        user = driver.user
        driver.delete()
        user.delete()
        return Response({"message": "Driver deleted successfully."}, status=status.HTTP_200_OK)
