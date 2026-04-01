from django.conf import settings
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import PendingCompanyRegistration
from apps.billing.serializers import RegistrationOnlySerializer
from apps.billing.services import create_subscription_order


class CreateRegistrationOrderAPIView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @swagger_auto_schema(
        tags=["Billing"],
        operation_summary="Create registration payment order",
        operation_description="Create Razorpay order for verified registration when plan is paid.",
        request_body=RegistrationOnlySerializer,
        responses={
            200: openapi.Response(
                description="Order status",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "requires_payment": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "order_id": openapi.Schema(type=openapi.TYPE_STRING),
                        "amount": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "currency": openapi.Schema(type=openapi.TYPE_STRING),
                        "key": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: "OTP not verified or invalid registration",
        },
    )
    def post(self, request):
        serializer = RegistrationOnlySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        registration = PendingCompanyRegistration.objects.filter(
            id=serializer.validated_data["registration_id"]
        ).select_related("plan").first()

        if not registration.is_verified:
            return Response({"message": "Verify OTP before creating order."}, status=status.HTTP_400_BAD_REQUEST)

        if registration.plan.price <= 0:
            return Response(
                {"requires_payment": False, "message": "No payment required for selected plan."},
                status=status.HTTP_200_OK,
            )

        order = create_subscription_order(registration.plan, receipt=f"reg_{registration.id}")
        registration.payment_order_id = order["id"]
        registration.save(update_fields=["payment_order_id", "updated_at"])

        return Response(
            {
                "requires_payment": True,
                "message": "Payment order created successfully.",
                "order_id": order["id"],
                "amount": order["amount"],
                "currency": order["currency"],
                "key": settings.RAZORPAY_KEY_ID,
            },
            status=status.HTTP_200_OK,
        )
