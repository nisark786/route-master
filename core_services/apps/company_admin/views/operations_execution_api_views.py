from datetime import datetime, time
from decimal import Decimal

from django.db.models import Q, Sum
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.exceptions import NotFound, ValidationError

from apps.company_admin.models import DriverAssignment
from apps.driver.models import DriverAssignmentInventoryItem, DriverRouteRun, DriverRunStop

from .base import CompanyAdminAPIView


def _parse_date(date_raw):
    if not date_raw:
        return None
    try:
        return datetime.strptime(date_raw, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValidationError({"date": ["Use YYYY-MM-DD format."]}) from exc


def _to_iso(dt):
    if not dt:
        return None
    return dt.isoformat()


class CompanyOperationExecutionListAPIView(CompanyAdminAPIView):
    required_permission = "driver_assignment.view"

    @swagger_auto_schema(
        tags=["Company Admin Operations"],
        operation_summary="List route execution operations",
        manual_parameters=[
            openapi.Parameter("date", openapi.IN_QUERY, type=openapi.TYPE_STRING, description="YYYY-MM-DD"),
            openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter(
                "status",
                openapi.IN_QUERY,
                type=openapi.TYPE_STRING,
                enum=["all", "ASSIGNED", "IN_ROUTE", "COMPLETED", "CANCELLED"],
            ),
        ],
        responses={200: "Operations loaded"},
    )
    def get(self, request):
        requested_date = _parse_date(request.query_params.get("date"))
        search = (request.query_params.get("search") or "").strip()
        status_filter = (request.query_params.get("status") or "all").strip().upper()
        if status_filter not in {"ALL", "ASSIGNED", "IN_ROUTE", "COMPLETED", "CANCELLED"}:
            raise ValidationError({"status": ["Invalid status filter."]})

        assignments_qs = (
            DriverAssignment.objects.filter(
                driver__user__company_id=request.user.company_id,
            )
            .select_related("driver", "driver__user", "route", "vehicle")
            .order_by("-scheduled_at", "-created_at")
        )
        if requested_date is not None:
            start_dt = timezone.make_aware(datetime.combine(requested_date, time.min))
            end_dt = timezone.make_aware(datetime.combine(requested_date, time.max))
            assignments_qs = assignments_qs.filter(
                Q(scheduled_at__range=(start_dt, end_dt))
                | Q(route_run__started_at__range=(start_dt, end_dt))
                | Q(route_run__completed_at__range=(start_dt, end_dt))
                | Q(route_run__stops__check_in_at__range=(start_dt, end_dt))
                | Q(route_run__stops__check_out_at__range=(start_dt, end_dt))
                | Q(route_run__stops__skipped_at__range=(start_dt, end_dt))
            ).distinct()

        if status_filter != "ALL":
            assignments_qs = assignments_qs.filter(status=status_filter)

        if search:
            assignments_qs = assignments_qs.filter(
                Q(driver__name__icontains=search)
                | Q(driver__user__mobile_number__icontains=search)
                | Q(route__route_name__icontains=search)
                | Q(vehicle__name__icontains=search)
                | Q(vehicle__number_plate__icontains=search)
            )

        assignments = list(assignments_qs)
        assignment_ids = [item.id for item in assignments]

        runs = (
            DriverRouteRun.objects.filter(assignment_id__in=assignment_ids)
            .select_related("assignment")
            .order_by("-started_at")
        )
        run_by_assignment_id = {run.assignment_id: run for run in runs}

        stops = DriverRunStop.objects.filter(run__assignment_id__in=assignment_ids).values("run__assignment_id", "status")
        stop_counts = {}
        for stop in stops:
            assignment_id = stop["run__assignment_id"]
            bucket = stop_counts.setdefault(
                assignment_id,
                {"total": 0, "completed": 0, "checked_in": 0, "pending": 0, "skipped": 0},
            )
            bucket["total"] += 1
            status = stop["status"]
            if status == DriverRunStop.STATUS_COMPLETED:
                bucket["completed"] += 1
            elif status == DriverRunStop.STATUS_CHECKED_IN:
                bucket["checked_in"] += 1
            elif status == DriverRunStop.STATUS_PENDING:
                bucket["pending"] += 1
            elif status == DriverRunStop.STATUS_SKIPPED:
                bucket["skipped"] += 1

        invoice_by_assignment_id = {
            item["run__assignment_id"]: Decimal(item["total"] or "0")
            for item in DriverRunStop.objects.filter(run__assignment_id__in=assignment_ids).values("run__assignment_id").annotate(
                total=Sum("invoice_total")
            )
        }

        inventory_loaded_by_assignment_id = {
            item["assignment_id"]: int(item["total_qty"] or 0)
            for item in DriverAssignmentInventoryItem.objects.filter(assignment_id__in=assignment_ids).values("assignment_id").annotate(
                total_qty=Sum("quantity")
            )
        }

        results = []
        for assignment in assignments:
            run = run_by_assignment_id.get(assignment.id)
            counts = stop_counts.get(assignment.id, {"total": 0, "completed": 0, "checked_in": 0, "pending": 0, "skipped": 0})

            current_stop = (
                DriverRunStop.objects.filter(
                    run__assignment_id=assignment.id,
                    status__in=[DriverRunStop.STATUS_CHECKED_IN, DriverRunStop.STATUS_PENDING],
                )
                .select_related("shop")
                .order_by("position")
                .first()
            )

            results.append(
                {
                    "assignment_id": str(assignment.id),
                    "scheduled_at": _to_iso(assignment.scheduled_at),
                    "status": assignment.status,
                    "driver": {
                        "id": str(assignment.driver_id),
                        "name": assignment.driver.name,
                        "mobile_number": assignment.driver.user.mobile_number,
                    },
                    "route": {
                        "id": str(assignment.route_id),
                        "name": assignment.route.route_name,
                        "start_point": assignment.route.start_point,
                        "end_point": assignment.route.end_point,
                    },
                    "vehicle": {
                        "id": str(assignment.vehicle_id),
                        "name": assignment.vehicle.name,
                        "number_plate": assignment.vehicle.number_plate,
                    },
                    "run": {
                        "id": str(run.id) if run else None,
                        "status": run.status if run else None,
                        "started_at": _to_iso(run.started_at) if run else None,
                        "completed_at": _to_iso(run.completed_at) if run else None,
                    },
                    "progress": counts,
                    "current_stop": {
                        "shop_id": str(current_stop.shop_id),
                        "shop_name": current_stop.shop.name,
                        "position": current_stop.position,
                        "status": current_stop.status,
                    }
                    if current_stop
                    else None,
                    "invoice_total": f"{invoice_by_assignment_id.get(assignment.id, Decimal('0.00')):.2f}",
                    "inventory_loaded_quantity": inventory_loaded_by_assignment_id.get(assignment.id, 0),
                }
            )

        kpis = {
            "total_assignments": len(assignments),
            "assigned_count": sum(1 for item in assignments if item.status == DriverAssignment.STATUS_ASSIGNED),
            "in_route_count": sum(1 for item in assignments if item.status == DriverAssignment.STATUS_IN_ROUTE),
            "completed_count": sum(1 for item in assignments if item.status == DriverAssignment.STATUS_COMPLETED),
            "cancelled_count": sum(1 for item in assignments if item.status == DriverAssignment.STATUS_CANCELLED),
            "total_invoice_amount": f"{sum((invoice_by_assignment_id.get(item.id, Decimal('0.00')) for item in assignments), Decimal('0.00')):.2f}",
        }

        return self.success_response(
            data={
                "date": requested_date.isoformat() if requested_date else None,
                "kpis": kpis,
                "results": results,
            },
            message="Operations loaded.",
        )


class CompanyOperationExecutionDetailAPIView(CompanyAdminAPIView):
    required_permission = "driver_assignment.view"

    @swagger_auto_schema(
        tags=["Company Admin Operations"],
        operation_summary="Get route execution detail by assignment",
        manual_parameters=[openapi.Parameter("assignment_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        responses={200: "Execution detail loaded"},
    )
    def get(self, request, assignment_id):
        assignment = (
            DriverAssignment.objects.filter(id=assignment_id, driver__user__company_id=request.user.company_id)
            .select_related("driver", "driver__user", "route", "vehicle")
            .first()
        )
        if not assignment:
            raise NotFound("Assignment not found.")

        run = (
            DriverRouteRun.objects.filter(assignment_id=assignment.id)
            .select_related("route", "vehicle", "driver")
            .order_by("-started_at")
            .first()
        )
        stops = list(
            DriverRunStop.objects.filter(run_id=run.id if run else None)
            .select_related("shop")
            .order_by("position")
        ) if run else []

        loaded_inventory_rows = list(
            DriverAssignmentInventoryItem.objects.filter(assignment_id=assignment.id)
            .select_related("product")
            .order_by("product__name")
        )
        loaded_inventory = [
            {
                "product_id": str(row.product_id),
                "product_name": row.product.name,
                "quantity": int(row.quantity),
                "rate": f"{Decimal(row.product.rate):.2f}",
            }
            for row in loaded_inventory_rows
        ]

        stops_payload = []
        events = []
        for stop in stops:
            invoice_url = request.build_absolute_uri(stop.invoice_file.url) if stop.invoice_file else ""
            stops_payload.append(
                {
                    "stop_id": str(stop.id),
                    "position": stop.position,
                    "status": stop.status,
                    "shop": {
                        "id": str(stop.shop_id),
                        "name": stop.shop.name,
                        "owner_name": stop.shop.owner_name,
                        "owner_mobile_number": stop.shop.owner_mobile_number,
                        "location_display_name": stop.shop.location_display_name,
                        "address": stop.shop.address,
                    },
                    "check_in_at": _to_iso(stop.check_in_at),
                    "check_out_at": _to_iso(stop.check_out_at),
                    "skipped_at": _to_iso(stop.skipped_at),
                    "skip_reason": stop.skip_reason,
                    "ordered_items": stop.ordered_items or [],
                    "invoice_number": stop.invoice_number,
                    "invoice_total": f"{Decimal(stop.invoice_total or 0):.2f}",
                    "invoice_url": invoice_url,
                }
            )

            if stop.check_in_at:
                events.append(
                    {
                        "type": "CHECK_IN",
                        "timestamp": _to_iso(stop.check_in_at),
                        "label": f"Checked in at {stop.shop.name}",
                    }
                )
            if stop.skipped_at:
                events.append(
                    {
                        "type": "SKIP",
                        "timestamp": _to_iso(stop.skipped_at),
                        "label": f"Skipped {stop.shop.name}",
                        "meta": {"reason": stop.skip_reason},
                    }
                )
            if stop.invoice_number:
                events.append(
                    {
                        "type": "INVOICE",
                        "timestamp": _to_iso(stop.updated_at),
                        "label": f"Invoice {stop.invoice_number} generated",
                        "meta": {"shop_name": stop.shop.name, "invoice_total": f"{Decimal(stop.invoice_total or 0):.2f}"},
                    }
                )
            if stop.check_out_at:
                events.append(
                    {
                        "type": "CHECK_OUT",
                        "timestamp": _to_iso(stop.check_out_at),
                        "label": f"Checked out from {stop.shop.name}",
                    }
                )

        if run and run.started_at:
            events.append(
                {
                    "type": "ROUTE_STARTED",
                    "timestamp": _to_iso(run.started_at),
                    "label": f"Route {assignment.route.route_name} started",
                }
            )
        if run and run.completed_at:
            events.append(
                {
                    "type": "ROUTE_COMPLETED",
                    "timestamp": _to_iso(run.completed_at),
                    "label": f"Route {assignment.route.route_name} completed",
                }
            )
        events.sort(key=lambda item: item.get("timestamp") or "")

        invoice_total = sum((Decimal(stop.invoice_total or 0) for stop in stops), Decimal("0.00"))
        return self.success_response(
            data={
                "assignment": {
                    "id": str(assignment.id),
                    "status": assignment.status,
                    "scheduled_at": _to_iso(assignment.scheduled_at),
                    "notes": assignment.notes,
                    "driver": {
                        "id": str(assignment.driver_id),
                        "name": assignment.driver.name,
                        "mobile_number": assignment.driver.user.mobile_number,
                    },
                    "route": {
                        "id": str(assignment.route_id),
                        "name": assignment.route.route_name,
                        "start_point": assignment.route.start_point,
                        "end_point": assignment.route.end_point,
                    },
                    "vehicle": {
                        "id": str(assignment.vehicle_id),
                        "name": assignment.vehicle.name,
                        "number_plate": assignment.vehicle.number_plate,
                    },
                },
                "run": {
                    "id": str(run.id) if run else None,
                    "status": run.status if run else None,
                    "started_at": _to_iso(run.started_at) if run else None,
                    "completed_at": _to_iso(run.completed_at) if run else None,
                },
                "stops": stops_payload,
                "inventory": {
                    "loaded_items": loaded_inventory,
                    "loaded_quantity_total": sum((int(item["quantity"]) for item in loaded_inventory), 0),
                },
                "summary": {
                    "total_stops": len(stops),
                    "completed_stops": sum(1 for stop in stops if stop.status == DriverRunStop.STATUS_COMPLETED),
                    "checked_in_stops": sum(1 for stop in stops if stop.status == DriverRunStop.STATUS_CHECKED_IN),
                    "pending_stops": sum(1 for stop in stops if stop.status == DriverRunStop.STATUS_PENDING),
                    "skipped_stops": sum(1 for stop in stops if stop.status == DriverRunStop.STATUS_SKIPPED),
                    "invoice_total": f"{invoice_total:.2f}",
                },
                "events": events,
            },
            message="Execution detail loaded.",
        )
