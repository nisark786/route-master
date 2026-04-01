from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing.models import PaymentTransaction


class CompanyBillingTransactionListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        tags=["Billing"],
        operation_summary="List company billing transactions",
        operation_description="Return recent payment/invoice transactions for authenticated company admin.",
        responses={
            200: openapi.Response(
                description="Billing transactions loaded",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "results": openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    "id": openapi.Schema(type=openapi.TYPE_INTEGER),
                                    "invoice_number": openapi.Schema(type=openapi.TYPE_STRING),
                                    "amount": openapi.Schema(type=openapi.TYPE_STRING),
                                    "currency": openapi.Schema(type=openapi.TYPE_STRING),
                                    "status": openapi.Schema(type=openapi.TYPE_STRING),
                                    "provider": openapi.Schema(type=openapi.TYPE_STRING),
                                    "paid_at": openapi.Schema(type=openapi.TYPE_STRING, format=openapi.FORMAT_DATETIME),
                                    "plan_code": openapi.Schema(type=openapi.TYPE_STRING),
                                },
                            ),
                        )
                    },
                ),
            ),
            403: "Only company admin can access billing transactions",
        },
    )
    def get(self, request):
        if request.user.role != "COMPANY_ADMIN" or not request.user.company_id:
            return Response(
                {"message": "Only company admin can access billing transactions."},
                status=status.HTTP_403_FORBIDDEN,
            )

        txs = (
            PaymentTransaction.objects.filter(company_id=request.user.company_id)
            .order_by("-paid_at")
            .values(
                "id",
                "invoice_number",
                "amount",
                "currency",
                "status",
                "provider",
                "paid_at",
                "metadata",
            )[:50]
        )
        payload = []
        for tx in txs:
            payload.append(
                {
                    "id": tx["id"],
                    "invoice_number": tx["invoice_number"],
                    "amount": str(tx["amount"]),
                    "currency": tx["currency"],
                    "status": tx["status"],
                    "provider": tx["provider"],
                    "paid_at": tx["paid_at"],
                    "plan_code": (tx.get("metadata") or {}).get("plan_code"),
                }
            )
        return Response({"results": payload}, status=status.HTTP_200_OK)
