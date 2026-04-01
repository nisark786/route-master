from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.company_admin.models import Driver
from apps.company_admin.serializers import TemporaryPasswordResetSerializer

from .base import CompanyAdminAPIView


class DriverResetPasswordAPIView(CompanyAdminAPIView):
    required_permission = "driver.reset_password"

    def _get_driver(self, company_id, driver_id):
        driver = Driver.objects.filter(user__company_id=company_id, id=driver_id).select_related("user").first()
        if not driver:
            raise NotFound("Driver not found.")
        return driver

    @swagger_auto_schema(
        tags=["Company Admin Drivers"],
        operation_summary="Reset driver temporary password",
        manual_parameters=[openapi.Parameter("driver_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        request_body=TemporaryPasswordResetSerializer,
        responses={200: "Password reset"},
    )
    def post(self, request, driver_id):
        driver = self._get_driver(request.user.company_id, driver_id)
        serializer = TemporaryPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        temporary_password = serializer.validated_data["temporary_password"].strip()
        driver.user.set_password(temporary_password)
        driver.user.must_change_password = True
        driver.user.save(update_fields=["password", "must_change_password"])

        return Response(
            {
                "driver_id": str(driver.id),
                "mobile_number": driver.user.mobile_number,
                "must_change_password": True,
                "message": "Driver temporary password reset successfully.",
            },
            status=status.HTTP_200_OK,
        )
