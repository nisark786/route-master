from django.conf import settings
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from razorpay.errors import BadRequestError

from apps.billing.serializers import RenewSubscriptionSerializer
from apps.billing.services import create_subscription_order


class CreateSubscriptionRenewalOrderAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Billing"],
        operation_summary="Create subscription renewal payment order",
        operation_description="Create Razorpay order for renewing current company subscription.",
        request_body=RenewSubscriptionSerializer,
        responses={
            200: openapi.Response(
                description="Renewal order status",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "requires_payment": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        "message": openapi.Schema(type=openapi.TYPE_STRING),
                        "order_id": openapi.Schema(type=openapi.TYPE_STRING),
                        "amount": openapi.Schema(type=openapi.TYPE_INTEGER),
                        "currency": openapi.Schema(type=openapi.TYPE_STRING),
                        "key": openapi.Schema(type=openapi.TYPE_STRING),
                        "plan_code": openapi.Schema(type=openapi.TYPE_STRING),
                    },
                ),
            ),
            400: "Validation error",
            403: "Only company admin can renew subscription",
        },
    )
    def post(self, request):
        if request.user.role != "COMPANY_ADMIN" or not request.user.company_id:
            return Response(
                {"message": "Only company admin can renew subscription."},
                status=status.HTTP_403_FORBIDDEN,
            )

        serializer = RenewSubscriptionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan = serializer.context["plan"]

        if plan.price <= 0:
            return Response(
                {
                    "requires_payment": False,
                    "message": "No payment required for selected plan.",
                    "plan_code": plan.code,
                },
                status=status.HTTP_200_OK,
            )

        company_suffix = str(request.user.company_id).replace("-", "")[:8]
        receipt = f"ren_{company_suffix}_{int(timezone.now().timestamp())}"[:40]
        try:
            order = create_subscription_order(plan, receipt=receipt)
        except BadRequestError as exc:
            return Response(
                {"message": f"Unable to create renewal order: {str(exc)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception:
            return Response(
                {"message": "Unable to create renewal order at the moment. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "requires_payment": True,
                "message": "Renewal payment order created successfully.",
                "order_id": order["id"],
                "amount": order["amount"],
                "currency": order["currency"],
                "key": settings.RAZORPAY_KEY_ID,
                "plan_code": plan.code,
            },
            status=status.HTTP_200_OK,
        )
