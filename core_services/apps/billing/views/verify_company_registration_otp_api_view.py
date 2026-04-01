from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import PendingCompanyRegistration
from apps.billing.serializers import VerifyOtpSerializer
from apps.billing.services import delete_registration_otp


class VerifyCompanyRegistrationOtpAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        tags=["Billing"],
        operation_summary="Verify registration OTP",
        operation_description="Verify OTP for a pending company registration.",
        request_body=VerifyOtpSerializer,
        responses={
            200: openapi.Response(
                description="OTP verified",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "registration_id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: "Invalid/expired OTP",
        },
    )
    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = serializer.validated_data["registration"]
        registration.is_verified = True
        registration.status = PendingCompanyRegistration.STATUS_PENDING_PAYMENT
        registration.save(update_fields=["is_verified", "status", "updated_at"])
        delete_registration_otp(registration.id)

        return Response(
            {"registration_id": registration.id, "message": "OTP verified successfully."},
            status=status.HTTP_200_OK,
        )
