from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.driver.models import DriverRunStop
from apps.core.permissions import HasPermissionCode


class ShopOwnerAPIView(APIView):
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_permission = "shop_owner.access"

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not request.user.company_id:
            raise PermissionDenied("Shop owner is not linked to a company.")

    def success_response(self, data=None, message="Request completed successfully.", status_code=status.HTTP_200_OK):
        return Response({"success": True, "message": message, "data": data}, status=status_code)


def _build_invoice_url(request, stop):
    if not stop.invoice_file:
        return ""
    return request.build_absolute_uri(stop.invoice_file.url)


def _serialize_stop(request, stop):
    run = stop.run
    route = run.route
    driver = run.driver
    return {
        "stop_id": stop.id,
        "status": stop.status,
        "position": stop.position,
        "shop_id": stop.shop_id,
        "shop_name": stop.shop.name,
        "route_id": route.id,
        "route_name": route.route_name,
        "driver_id": driver.id,
        "driver_name": driver.name,
        "driver_mobile_number": driver.user.mobile_number,
        "vehicle_name": run.vehicle.name,
        "vehicle_number_plate": run.vehicle.number_plate,
        "check_in_at": stop.check_in_at,
        "check_out_at": stop.check_out_at,
        "invoice_number": stop.invoice_number,
        "invoice_total": stop.invoice_total,
        "invoice_url": _build_invoice_url(request, stop),
        "ordered_items": stop.ordered_items or [],
        "preordered_items": stop.preordered_items or [],
    }


def _get_shop_owner_stops_queryset(user):
    return (
        DriverRunStop.objects.filter(
            shop__owner_user_id=user.id,
            shop__company_id=user.company_id,
        )
        .select_related(
            "shop",
            "run",
            "run__route",
            "run__vehicle",
            "run__driver",
            "run__driver__user",
        )
        .order_by("-updated_at", "-created_at")
    )


class ShopOwnerDashboardAPIView(ShopOwnerAPIView):
    @swagger_auto_schema(
        tags=["Shop Owner App"],
        operation_summary="Get shop owner dashboard metrics",
        responses={200: "Dashboard loaded"},
    )
    def get(self, request):
        qs = _get_shop_owner_stops_queryset(request.user)
        cache_key = f"shop_owner:dashboard:{request.user.id}"
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return self.success_response(data=cached_payload, message="Dashboard loaded.")

        today = timezone.localdate()
        metrics = qs.aggregate(
            pending_deliveries=Count("id", filter=Q(status=DriverRunStop.STATUS_PENDING)),
            checked_in_deliveries=Count("id", filter=Q(status=DriverRunStop.STATUS_CHECKED_IN)),
            completed_today=Count(
                "id",
                filter=Q(
                    status=DriverRunStop.STATUS_COMPLETED,
                    check_out_at__date=today,
                ),
            ),
            open_deliveries=Count(
                "id",
                filter=Q(status__in=[DriverRunStop.STATUS_PENDING, DriverRunStop.STATUS_CHECKED_IN]),
            ),
        )

        recent_invoices = [
            _serialize_stop(request, stop)
            for stop in qs.filter(status=DriverRunStop.STATUS_COMPLETED).exclude(invoice_number="")[:10]
        ]

        payload = {"metrics": metrics, "recent_invoices": recent_invoices}
        cache.set(cache_key, payload, timeout=60)

        return self.success_response(data=payload, message="Dashboard loaded.")


class ShopOwnerDeliveryListAPIView(ShopOwnerAPIView):
    @swagger_auto_schema(
        tags=["Shop Owner App"],
        operation_summary="List deliveries for shop owner",
        manual_parameters=[
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                description="Filter by stop status: PENDING, CHECKED_IN, COMPLETED",
                type=openapi.TYPE_STRING,
                required=False,
            ),
            openapi.Parameter(
                "has_invoice",
                openapi.IN_QUERY,
                description="Filter invoice availability: true/false",
                type=openapi.TYPE_STRING,
                required=False,
            ),
        ],
        responses={200: "Deliveries loaded"},
    )
    def get(self, request):
        qs = _get_shop_owner_stops_queryset(request.user)

        status_filter = (request.query_params.get("status") or "").strip().upper()
        if status_filter in {
            DriverRunStop.STATUS_PENDING,
            DriverRunStop.STATUS_CHECKED_IN,
            DriverRunStop.STATUS_COMPLETED,
        }:
            qs = qs.filter(status=status_filter)

        has_invoice = (request.query_params.get("has_invoice") or "").strip().lower()
        if has_invoice == "true":
            qs = qs.exclude(invoice_number="")
        elif has_invoice == "false":
            qs = qs.filter(invoice_number="")

        data = [_serialize_stop(request, stop) for stop in qs[:100]]
        return self.success_response(data=data, message="Deliveries loaded.")


class ShopOwnerDeliveryDetailAPIView(ShopOwnerAPIView):
    @swagger_auto_schema(
        tags=["Shop Owner App"],
        operation_summary="Get delivery details for a specific stop",
        manual_parameters=[
            openapi.Parameter("stop_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True),
        ],
        responses={200: "Delivery details loaded", 404: "Delivery not found"},
    )
    def get(self, request, stop_id):
        stop = _get_shop_owner_stops_queryset(request.user).filter(id=stop_id).first()
        if not stop:
            raise NotFound("Delivery stop not found.")
        return self.success_response(data=_serialize_stop(request, stop), message="Delivery details loaded.")
