from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.authentication.models import User
from apps.billing.models import (
    CompanySubscription,
    PaymentTransaction,
    PendingCompanyRegistration,
    PlanChangeLog,
)
from apps.billing.serializers import CompleteRegistrationSerializer
from apps.billing.services import generate_tokens_for_user, verify_razorpay_signature
from apps.company.models import Company, CompanyActivityLog


class CompleteCompanyRegistrationAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        tags=["Billing"],
        operation_summary="Complete company registration",
        operation_description="Verify payment (if required), create company/user/subscription, and return auth tokens.",
        request_body=CompleteRegistrationSerializer,
        responses={
            201: openapi.Response(
                description="Registration completed",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "access": openapi.Schema(type=openapi.TYPE_STRING),
                        "role": openapi.Schema(type=openapi.TYPE_STRING),
                        "email": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_EMAIL),
                        "company_id": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_UUID),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: "Invalid registration or payment verification failed",
            404: "Registration not found",
        },
    )
    @transaction.atomic
    def post(self, request):
        serializer = CompleteRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        registration = PendingCompanyRegistration.objects.select_related("plan").filter(
            id=data["registration_id"]
        ).first()
        if not registration:
            return Response({"message": "Registration not found."}, status=status.HTTP_404_NOT_FOUND)
        if registration.status == PendingCompanyRegistration.STATUS_COMPLETED:
            return Response({"message": "Registration already completed."}, status=status.HTTP_400_BAD_REQUEST)
        if not registration.is_verified:
            return Response({"message": "OTP is not verified."}, status=status.HTTP_400_BAD_REQUEST)

        if registration.plan.price > 0:
            order_id = data.get("razorpay_order_id", "")
            payment_id = data.get("razorpay_payment_id", "")
            signature = data.get("razorpay_signature", "")
            if not all([order_id, payment_id, signature]):
                return Response({"message": "Payment details are required."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                verify_razorpay_signature(order_id, payment_id, signature)
            except Exception:
                return Response({"message": "Payment verification failed."}, status=status.HTTP_400_BAD_REQUEST)
            registration.payment_order_id = order_id
            registration.payment_id = payment_id
            registration.payment_signature = signature
        else:
            registration.payment_order_id = registration.payment_order_id or "TRIAL"
            registration.payment_id = registration.payment_id or "TRIAL"
            registration.payment_signature = registration.payment_signature or "TRIAL"

        company = Company.objects.create(
            name=registration.company_name,
            official_email=registration.official_email,
            phone=registration.phone,
            address=registration.address,
            is_active=True,
            is_email_verified=True,
        )

        user = User.objects.create(
            email=registration.admin_email,
            role="COMPANY_ADMIN",
            company=company,
            is_active=True,
        )
        user.password = registration.admin_password_hash
        user.save(update_fields=["password"])

        subscription = CompanySubscription.objects.create(
            company=company,
            plan=registration.plan,
            razorpay_order_id=registration.payment_order_id,
            razorpay_payment_id=registration.payment_id,
            razorpay_signature=registration.payment_signature,
            end_date=timezone.now() + timedelta(days=registration.plan.duration_days),
            amount_paid=registration.plan.price,
            currency="INR",
            is_active=True,
        )

        invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{str(company.id)[:8]}"
        payment_status = (
            PaymentTransaction.STATUS_SUCCESS
            if registration.plan.price > 0 or registration.plan.code == "trial"
            else PaymentTransaction.STATUS_FAILED
        )
        PaymentTransaction.objects.create(
            company=company,
            subscription=subscription,
            provider="razorpay",
            order_id=registration.payment_order_id,
            payment_id=registration.payment_id,
            invoice_number=invoice_number,
            amount=registration.plan.price,
            currency="INR",
            status=payment_status,
            metadata={"plan_code": registration.plan.code},
        )

        PlanChangeLog.objects.create(
            company=company,
            old_plan=None,
            new_plan=registration.plan,
            changed_by=user,
            reason="Initial company onboarding subscription.",
        )
        CompanyActivityLog.objects.create(
            company=company,
            actor=user,
            action="COMPANY_ONBOARDED",
            details={"plan_code": registration.plan.code},
        )
        cache.delete(f"billing:company-subscription-state:{company.id}")
        cache.delete(f"company_profile:{company.id}")
        cache.delete(f"user_profile:{user.id}")

        registration.status = PendingCompanyRegistration.STATUS_COMPLETED
        registration.save(update_fields=["status", "payment_order_id", "payment_id", "payment_signature", "updated_at"])

        tokens = generate_tokens_for_user(user)
        response = Response(
            {
                "access": tokens["access"],
                "role": user.role,
                "email": user.email,
                "company_id": user.company_id,
                "message": "Company registration completed successfully.",
            },
            status=status.HTTP_201_CREATED,
        )
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh"],
            httponly=True,
            secure=settings.REFRESH_COOKIE_SECURE,
            samesite=settings.REFRESH_COOKIE_SAMESITE,
            domain=settings.REFRESH_COOKIE_DOMAIN,
        )
        return response
