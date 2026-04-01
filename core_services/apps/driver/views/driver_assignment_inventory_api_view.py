from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import ValidationError

from apps.company_admin.models import DriverAssignment, Product
from apps.driver.models import DriverAssignmentInventoryItem
from apps.driver.serializers import DriverAssignmentInventoryUpdateSerializer
from apps.driver.views.helpers import get_assignment_for_driver, get_driver_for_user

from .base import DriverAPIView


class DriverAssignmentInventoryAPIView(DriverAPIView):
    @swagger_auto_schema(
        tags=["Driver App"],
        operation_summary="Get products and loaded inventory for an assignment",
        manual_parameters=[openapi.Parameter("assignment_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        responses={200: "Inventory loaded"},
    )
    def get(self, request, assignment_id):
        driver = get_driver_for_user(request.user)
        assignment = get_assignment_for_driver(driver, assignment_id)
        self._validate_assignment_state(assignment)
        return self.success_response(data=self._build_inventory_payload(request, assignment), message="Inventory loaded.")

    @swagger_auto_schema(
        tags=["Driver App"],
        operation_summary="Save assignment inventory and update stock",
        manual_parameters=[openapi.Parameter("assignment_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        request_body=DriverAssignmentInventoryUpdateSerializer,
        responses={200: "Inventory updated"},
    )
    @transaction.atomic
    def post(self, request, assignment_id):
        driver = get_driver_for_user(request.user)
        assignment = (
            DriverAssignment.objects.select_for_update()
            .select_related("route", "vehicle", "driver")
            .filter(id=assignment_id, driver_id=driver.id)
            .first()
        )
        if not assignment:
            raise ValidationError({"assignment": ["Assignment not found."]})
        self._validate_assignment_state(assignment)

        serializer = DriverAssignmentInventoryUpdateSerializer(data=request.data or {})
        serializer.is_valid(raise_exception=True)
        incoming_items = serializer.validated_data.get("items", [])

        requested_ids = {item["product_id"] for item in incoming_items}
        existing_rows = list(
            DriverAssignmentInventoryItem.objects.select_for_update()
            .filter(assignment_id=assignment.id)
            .select_related("product")
        )
        existing_map = {row.product_id: row for row in existing_rows}

        all_product_ids = set(requested_ids) | set(existing_map.keys())
        products = list(
            Product.objects.select_for_update()
            .filter(company_id=request.user.company_id, id__in=all_product_ids)
            .order_by("name")
        )
        product_map = {product.id: product for product in products}

        missing_ids = [str(product_id) for product_id in requested_ids if product_id not in product_map]
        if missing_ids:
            raise ValidationError({"items": ["Some products are invalid for this company."]})

        desired_map = {item["product_id"]: int(item["quantity"]) for item in incoming_items}
        for product_id in all_product_ids:
            current_qty = int(existing_map.get(product_id).quantity if product_id in existing_map else 0)
            desired_qty = int(desired_map.get(product_id, 0))
            delta = desired_qty - current_qty
            if delta <= 0:
                continue
            product = product_map.get(product_id)
            if not product or product.quantity_count < delta:
                raise ValidationError(
                    {
                        "items": [
                            f"Not enough stock for {product.name if product else 'a selected product'}.",
                        ]
                    }
                )

        for product_id in all_product_ids:
            product = product_map.get(product_id)
            row = existing_map.get(product_id)
            current_qty = int(row.quantity if row else 0)
            desired_qty = int(desired_map.get(product_id, 0))
            delta = desired_qty - current_qty

            if delta != 0 and product:
                product.quantity_count = int(product.quantity_count) - delta
                if product.quantity_count < 0:
                    raise ValidationError({"items": ["Stock cannot become negative."]})
                product.save(update_fields=["quantity_count", "updated_at"])

            if desired_qty <= 0:
                if row:
                    row.delete()
                continue

            if row:
                if row.quantity != desired_qty:
                    row.quantity = desired_qty
                    row.save(update_fields=["quantity", "updated_at"])
                continue

            DriverAssignmentInventoryItem.objects.create(
                assignment_id=assignment.id,
                driver_id=driver.id,
                product_id=product_id,
                quantity=desired_qty,
            )

        payload = self._build_inventory_payload(request, assignment)
        return self.success_response(data=payload, message="Inventory saved successfully.")

    def _validate_assignment_state(self, assignment):
        if assignment.status == DriverAssignment.STATUS_COMPLETED:
            raise ValidationError({"assignment": ["This assignment is already completed."]})
        if assignment.status == DriverAssignment.STATUS_CANCELLED:
            raise ValidationError({"assignment": ["This assignment is cancelled."]})

    def _build_inventory_payload(self, request, assignment):
        rows = list(
            DriverAssignmentInventoryItem.objects.filter(assignment_id=assignment.id)
            .select_related("product")
            .order_by("product__name")
        )
        loaded_by_product_id = {row.product_id: int(row.quantity) for row in rows}

        products = Product.objects.filter(company_id=request.user.company_id).order_by("name")
        product_payload = []
        loaded_total = 0
        for product in products:
            loaded_qty = loaded_by_product_id.get(product.id, 0)
            loaded_total += loaded_qty
            product_payload.append(
                {
                    "id": product.id,
                    "name": product.name,
                    "rate": str(product.rate),
                    "quantity_count": product.quantity_count,
                    "loaded_quantity": loaded_qty,
                    "description": product.description,
                    "shelf_life": product.shelf_life,
                    "image": request.build_absolute_uri(product.image.url) if product.image else "",
                }
            )

        loaded_items_payload = [
            {
                "product_id": str(row.product_id),
                "product_name": row.product.name,
                "quantity": int(row.quantity),
            }
            for row in rows
        ]
        return {
            "assignment_id": assignment.id,
            "assignment_status": assignment.status,
            "products": product_payload,
            "loaded_items": loaded_items_payload,
            "loaded_items_count": len(loaded_items_payload),
            "loaded_quantity_total": loaded_total,
        }
