from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import PendingCompanyRegistration
from apps.billing.serializers import StartRegistrationSerializer
from apps.billing.services import (
    dispatch_registration_otp_background,
    generate_otp,
    store_registration_otp,
)


class StartCompanyRegistrationAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        tags=["Billing"],
        operation_summary="Start company registration",
        operation_description="Create pending registration and send OTP to company official email.",
        request_body=StartRegistrationSerializer,
        responses={
            201: openapi.Response(
                description="Registration started",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "registration_id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: "Validation error",
        },
    )
    def post(self, request):
        serializer = StartRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        otp = generate_otp()

        with transaction.atomic():
            registration = PendingCompanyRegistration.objects.create(
                company_name=data["company_name"],
                official_email=data["official_email"],
                phone=data.get("phone", ""),
                address=data.get("address", ""),
                admin_email=data["admin_email"],
                admin_password_hash=data["admin_password_hash"],
                plan=data["plan"],
                status=PendingCompanyRegistration.STATUS_PENDING_OTP,
            )
            store_registration_otp(registration.id, otp)
            transaction.on_commit(
                lambda: dispatch_registration_otp_background(registration.official_email, otp)
            )

        return Response(
            {"registration_id": registration.id, "message": "OTP sent to company official email."},
            status=status.HTTP_201_CREATED,
        )
