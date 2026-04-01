from decimal import Decimal

from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError

from apps.company_admin.models import Product
from apps.driver.models import DriverAssignmentInventoryItem, DriverRunStop
from apps.driver.serializers import DriverStopOrderCompleteSerializer
from apps.driver.services.invoice_service import build_invoice_number, create_invoice_pdf_file
from apps.driver.views.helpers import (
    build_whatsapp_url,
    get_driver_for_user,
    get_run_for_driver,
    get_stop_for_run,
)

from .base import DriverAPIView


class DriverStopCompleteOrderAPIView(DriverAPIView):
    @swagger_auto_schema(
        tags=["Driver App"],
        operation_summary="Complete shop order and create invoice",
        manual_parameters=[
            openapi.Parameter("assignment_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("shop_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
        ],
        request_body=DriverStopOrderCompleteSerializer,
        responses={200: "Order completed and invoice generated"},
    )
    @transaction.atomic
    def post(self, request, assignment_id, shop_id):
        driver = get_driver_for_user(request.user)
        run = get_run_for_driver(driver, assignment_id)
        stop = get_stop_for_run(run, shop_id)

        if stop.status == DriverRunStop.STATUS_COMPLETED:
            raise ValidationError({"stop": ["Stop is already completed."]})

        if stop.invoice_number:
            invoice_url = request.build_absolute_uri(stop.invoice_file.url) if stop.invoice_file else ""
            whatsapp_text = (
                f"Invoice {stop.invoice_number} for {stop.shop.name}. "
                f"Total: {stop.invoice_total:.2f}. {invoice_url}"
            )
            return self.success_response(
                data={
                    "stop_id": stop.id,
                    "invoice_number": stop.invoice_number,
                    "invoice_total": f"{stop.invoice_total:.2f}",
                    "invoice_url": invoice_url,
                    "whatsapp_url": build_whatsapp_url(stop.shop.owner_mobile_number, whatsapp_text),
                },
                message="Invoice already generated for this stop.",
            )

        if stop.status != DriverRunStop.STATUS_CHECKED_IN:
            raise ValidationError({"stop": ["Check in at the shop before recording orders."]})

        serializer = DriverStopOrderCompleteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        items = payload["items"]

        requested_product_ids = [item["product_id"] for item in items]
        products = Product.objects.filter(
            company_id=request.user.company_id,
            id__in=requested_product_ids,
        )
        product_map = {product.id: product for product in products}
        if len(product_map) != len(requested_product_ids):
            raise ValidationError({"items": ["Some products are invalid for this company."]})

        inventory_rows = list(
            DriverAssignmentInventoryItem.objects.select_for_update()
            .filter(
                assignment_id=run.assignment_id,
                product_id__in=requested_product_ids,
            )
            .select_related("product")
        )
        inventory_by_product_id = {row.product_id: row for row in inventory_rows}
        if len(inventory_by_product_id) != len(requested_product_ids):
            raise ValidationError({"items": ["Some selected products are not loaded in route inventory."]})

        line_items = []
        invoice_total = Decimal("0.00")
        for item in items:
            product = product_map[item["product_id"]]
            quantity = int(item["quantity"])
            inventory_row = inventory_by_product_id[item["product_id"]]
            if quantity > int(inventory_row.quantity):
                raise ValidationError(
                    {"items": [f"Insufficient route inventory for {product.name}."]},
                )
            line_total = Decimal(product.rate) * quantity
            invoice_total += line_total
            line_items.append(
                {
                    "product_id": str(product.id),
                    "name": product.name,
                    "rate": f"{Decimal(product.rate):.2f}",
                    "quantity": quantity,
                    "line_total": f"{line_total:.2f}",
                }
            )

        for item in items:
            inventory_row = inventory_by_product_id[item["product_id"]]
            quantity = int(item["quantity"])
            next_qty = int(inventory_row.quantity) - quantity
            inventory_row.quantity = next_qty
            inventory_row.save(update_fields=["quantity", "updated_at"])

        invoice_number = build_invoice_number(run.id, stop.position)
        filename, content = create_invoice_pdf_file(
            invoice_number=invoice_number,
            company_name=request.user.company.name,
            shop_name=stop.shop.name,
            driver_name=driver.name,
            route_name=run.route.route_name,
            items=line_items,
        )
        stop.invoice_file.save(filename, content, save=False)
        stop.invoice_number = invoice_number
        stop.invoice_total = invoice_total
        stop.ordered_items = line_items
        stop.save(update_fields=["invoice_file", "invoice_number", "invoice_total", "ordered_items", "updated_at"])

        invoice_url = request.build_absolute_uri(stop.invoice_file.url) if stop.invoice_file else ""
        whatsapp_text = f"Invoice {invoice_number} for {stop.shop.name}. Total: {invoice_total:.2f}. {invoice_url}"
        whatsapp_url = build_whatsapp_url(stop.shop.owner_mobile_number, whatsapp_text)

        return self.success_response(
            data={
                "stop_id": stop.id,
                "invoice_number": stop.invoice_number,
                "invoice_total": f"{invoice_total:.2f}",
                "invoice_url": invoice_url,
                "whatsapp_url": whatsapp_url,
            },
            message="Order recorded and invoice generated successfully.",
        )
