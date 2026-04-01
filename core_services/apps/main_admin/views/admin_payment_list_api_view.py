from django.core.paginator import Paginator
from django.db.models import Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.main_admin.serializers import PaymentListQuerySerializer
from apps.billing.models import PaymentTransaction

from .base import SuperAdminAPIView


class AdminPaymentListAPIView(SuperAdminAPIView):
    @swagger_auto_schema(
        tags=["Main Admin"],
        operation_summary="Payment logs",
        operation_description="Paginated payment transactions with status and search filters.",
        manual_parameters=[
            openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                enum=["all", "SUCCESS", "FAILED", "REFUNDED", "DISPUTED"],
            ),
            openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
            openapi.Parameter("page_size", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ],
        responses={200: "Paginated payment logs"},
    )
    def get(self, request):
        serializer = PaymentListQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        query = serializer.validated_data

        txs = PaymentTransaction.objects.select_related("company").all()
        if query["status"] != "all":
            txs = txs.filter(status=query["status"])
        search = query["search"].strip()
        if search:
            txs = txs.filter(
                Q(company__name__icontains=search)
                | Q(company__official_email__icontains=search)
                | Q(payment_id__icontains=search)
                | Q(order_id__icontains=search)
            )

        txs = txs.order_by("-paid_at")
        paginator = Paginator(txs, query["page_size"])
        page_obj = paginator.get_page(query["page"])

        return self.success_response(
            data={
                "count": paginator.count,
                "page": page_obj.number,
                "page_size": query["page_size"],
                "results": [
                    {
                        "id": tx.id,
                        "company_name": tx.company.name,
                        "company_email": tx.company.official_email,
                        "amount": str(tx.amount),
                        "currency": tx.currency,
                        "status": tx.status,
                        "payment_id": tx.payment_id,
                        "order_id": tx.order_id,
                        "invoice_number": tx.invoice_number,
                        "paid_at": tx.paid_at,
                    }
                    for tx in page_obj.object_list
                ],
            },
            message="Payments loaded.",
        )
