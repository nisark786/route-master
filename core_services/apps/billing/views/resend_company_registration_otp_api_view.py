from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import PendingCompanyRegistration
from apps.billing.serializers import RegistrationOnlySerializer
from apps.billing.services import generate_otp, queue_registration_otp, store_registration_otp


class ResendCompanyRegistrationOtpAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        tags=["Billing"],
        operation_summary="Resend registration OTP",
        operation_description="Resend a new OTP for an existing pending registration.",
        request_body=RegistrationOnlySerializer,
        responses={
            200: openapi.Response(
                description="OTP resent",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={"message": openapi.Schema(type=openapi.TYPE_STRING)},
                ),
            ),
            400: "Registration not available",
        },
    )
    def post(self, request):
        serializer = RegistrationOnlySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = PendingCompanyRegistration.objects.filter(
            id=serializer.validated_data["registration_id"]
        ).first()

        if not registration or registration.status == PendingCompanyRegistration.STATUS_COMPLETED:
            return Response({"message": "Registration not available."}, status=status.HTTP_400_BAD_REQUEST)

        otp = generate_otp()
        store_registration_otp(registration.id, otp)
        registration.status = PendingCompanyRegistration.STATUS_PENDING_OTP
        registration.is_verified = False
        registration.save(update_fields=["status", "is_verified", "updated_at"])

        queue_registration_otp(registration.official_email, otp)
        return Response({"message": "OTP resent successfully."}, status=status.HTTP_200_OK)
