from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema

from apps.company_admin.models import Product
from apps.driver.models import DriverAssignmentInventoryItem
from apps.driver.serializers import DriverRouteRunDetailSerializer
from apps.driver.views.helpers import get_driver_for_user, get_run_for_driver, get_stop_for_run

from .base import DriverAPIView


class DriverStopDetailAPIView(DriverAPIView):
    @swagger_auto_schema(
        tags=["Driver App"],
        operation_summary="Get stop details and available products",
        manual_parameters=[
            openapi.Parameter("assignment_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter("shop_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
        ],
        responses={200: "Stop details loaded"},
    )
    def get(self, request, assignment_id, shop_id):
        driver = get_driver_for_user(request.user)
        run = get_run_for_driver(driver, assignment_id)
        stop = get_stop_for_run(run, shop_id)

        request_context = {"request": request}
        run_payload = DriverRouteRunDetailSerializer(run, context=request_context).data
        stop_payload = next((item for item in run_payload["stops"] if str(item["shop_id"]) == str(shop_id)), None)

        loaded_inventory_rows = list(
            DriverAssignmentInventoryItem.objects.filter(
                assignment_id=run.assignment_id,
                quantity__gt=0,
            )
            .select_related("product")
            .order_by("product__name")
        )
        inventory_product_ids = [row.product_id for row in loaded_inventory_rows]
        products = Product.objects.filter(
            company_id=request.user.company_id,
            id__in=inventory_product_ids,
        ).order_by("name")
        loaded_qty_map = {row.product_id: int(row.quantity) for row in loaded_inventory_rows}
        product_payload = [
            {
                "id": product.id,
                "name": product.name,
                "rate": str(product.rate),
                "quantity_count": loaded_qty_map.get(product.id, 0),
                "description": product.description,
                "shelf_life": product.shelf_life,
                "image": request.build_absolute_uri(product.image.url) if product.image else "",
            }
            for product in products
        ]
        return self.success_response(
            data={
                "stop": stop_payload,
                "route_run": {
                    "id": run.id,
                    "status": run.status,
                    "next_pending_stop_id": run_payload["next_pending_stop_id"],
                },
                "products": product_payload,
                "preordered_items": (stop.preordered_items or []),
            },
            message="Stop details loaded.",
        )
