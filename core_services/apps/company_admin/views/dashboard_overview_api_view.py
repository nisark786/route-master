from datetime import timedelta

from django.core.cache import cache
from django.db.models import Count, F, Q
from django.db.models.functions import TruncDate
from django.utils import timezone
from drf_yasg.utils import swagger_auto_schema

from apps.company_admin.models import Driver, DriverAssignment, Product, Route, RouteShop, Shop, Vehicle
from apps.driver.models import DriverRouteRun
from apps.company_admin.services.cache import company_dashboard_cache_key

from .base import CompanyAdminAPIView


class CompanyAdminDashboardOverviewAPIView(CompanyAdminAPIView):
    required_permission = "company_admin.access"
    cache_timeout_seconds = 60

    @swagger_auto_schema(
        tags=["Company Admin Dashboard"],
        operation_summary="Company admin dashboard overview",
        operation_description="Return KPI cards, alerts, trends, and operational snapshots for the company-admin dashboard.",
        responses={200: "Dashboard overview loaded"},
    )
    def get(self, request):
        company_id = request.user.company_id
        cache_key = company_dashboard_cache_key(company_id)
        cached_payload = cache.get(cache_key)
        if cached_payload is not None:
            return self.success_response(data=cached_payload, message="Dashboard overview loaded.")

        now = timezone.now()
        today = timezone.localdate()
        week_start = today - timedelta(days=6)

        drivers = Driver.objects.filter(user__company_id=company_id).select_related("user")
        vehicles = Vehicle.objects.filter(company_id=company_id)
        routes = Route.objects.filter(company_id=company_id)
        shops = Shop.objects.filter(company_id=company_id)
        products = Product.objects.filter(company_id=company_id)
        assignments = (
            DriverAssignment.objects.filter(driver__user__company_id=company_id)
            .select_related("driver", "driver__user", "route", "vehicle")
        )
        route_runs = (
            DriverRouteRun.objects.filter(driver__user__company_id=company_id)
            .select_related("assignment", "driver", "route", "vehicle")
        )

        driver_counts = drivers.aggregate(
            total=Count("id"),
            available=Count("id", filter=Q(status=Driver.STATUS_AVAILABLE)),
            in_route=Count("id", filter=Q(status=Driver.STATUS_IN_ROUTE)),
            on_leave=Count("id", filter=Q(status=Driver.STATUS_ON_LEAVE)),
        )
        vehicle_counts = vehicles.aggregate(
            total=Count("id"),
            available=Count("id", filter=Q(status=Vehicle.STATUS_AVAILABLE)),
            on_route=Count("id", filter=Q(status=Vehicle.STATUS_ON_ROUTE)),
            renovation=Count("id", filter=Q(status=Vehicle.STATUS_RENOVATION)),
        )
        assignment_counts = assignments.aggregate(
            total=Count("id"),
            assigned=Count("id", filter=Q(status=DriverAssignment.STATUS_ASSIGNED)),
            in_route=Count("id", filter=Q(status=DriverAssignment.STATUS_IN_ROUTE)),
            completed=Count("id", filter=Q(status=DriverAssignment.STATUS_COMPLETED)),
            cancelled=Count("id", filter=Q(status=DriverAssignment.STATUS_CANCELLED)),
            today=Count("id", filter=Q(scheduled_at__date=today)),
            overdue=Count(
                "id",
                filter=Q(status=DriverAssignment.STATUS_ASSIGNED, scheduled_at__lt=now),
            ),
        )
        route_counts = routes.aggregate(total=Count("id"))
        shop_counts = shops.aggregate(
            total=Count("id"),
            without_route=Count("id", filter=Q(route_assignments__isnull=True)),
        )
        product_counts = products.aggregate(
            total=Count("id"),
            low_stock=Count("id", filter=Q(quantity_count__gt=0, quantity_count__lte=5)),
            zero_stock=Count("id", filter=Q(quantity_count=0)),
        )
        run_counts = route_runs.aggregate(
            active=Count("id", filter=Q(status=DriverRouteRun.STATUS_IN_PROGRESS)),
            completed_today=Count("id", filter=Q(status=DriverRouteRun.STATUS_COMPLETED, completed_at__date=today)),
        )

        unassigned_driver_count = drivers.filter(assignments__isnull=True).count()
        idle_vehicle_count = vehicles.filter(driver_assignments__isnull=True).count()
        routes_without_shops_count = routes.filter(route_shops__isnull=True).count()

        recent_assignment_rows = list(
            assignments.order_by("-updated_at", "-scheduled_at")[:6].values(
                "id",
                "status",
                "scheduled_at",
                "updated_at",
                driver_name=F("driver__name"),
                route_name=F("route__route_name"),
                vehicle_name=F("vehicle__name"),
            )
        )
        active_assignment_rows = list(
            route_runs.filter(status=DriverRouteRun.STATUS_IN_PROGRESS)
            .order_by("-started_at")[:5]
            .values(
                "id",
                "started_at",
                "status",
                driver_name=F("driver__name"),
                route_name=F("route__route_name"),
                vehicle_name=F("vehicle__name"),
            )
        )
        upcoming_assignment_rows = list(
            assignments.filter(status=DriverAssignment.STATUS_ASSIGNED, scheduled_at__gte=now)
            .order_by("scheduled_at")[:5]
            .values(
                "id",
                "scheduled_at",
                "status",
                driver_name=F("driver__name"),
                route_name=F("route__route_name"),
                vehicle_name=F("vehicle__name"),
            )
        )

        schedule_trend_rows = (
            assignments.filter(scheduled_at__date__gte=week_start, scheduled_at__date__lte=today)
            .annotate(day=TruncDate("scheduled_at"))
            .values("day")
            .annotate(
                assigned=Count("id"),
                completed=Count("id", filter=Q(status=DriverAssignment.STATUS_COMPLETED)),
                cancelled=Count("id", filter=Q(status=DriverAssignment.STATUS_CANCELLED)),
            )
            .order_by("day")
        )
        trend_map = {row["day"]: row for row in schedule_trend_rows}
        trend = []
        for offset in range(7):
            day = week_start + timedelta(days=offset)
            row = trend_map.get(day, {})
            trend.append(
                {
                    "date": day.isoformat(),
                    "label": day.strftime("%d %b"),
                    "assigned": row.get("assigned", 0),
                    "completed": row.get("completed", 0),
                    "cancelled": row.get("cancelled", 0),
                }
            )

        assignment_status = [
            {"key": "assigned", "label": "Assigned", "count": assignment_counts["assigned"] or 0, "tone": "blue"},
            {"key": "in_route", "label": "In Route", "count": assignment_counts["in_route"] or 0, "tone": "amber"},
            {"key": "completed", "label": "Completed", "count": assignment_counts["completed"] or 0, "tone": "emerald"},
        ]

        alerts = []
        if unassigned_driver_count:
            alerts.append(
                {
                    "id": "unassigned-drivers",
                    "severity": "warning",
                    "title": f"{unassigned_driver_count} driver(s) without assignments",
                    "description": "Available drivers are ready, but no schedule has been assigned yet.",
                    "action_to": "/company/schedule",
                    "action_label": "Assign routes",
                }
            )
        if idle_vehicle_count:
            alerts.append(
                {
                    "id": "idle-vehicles",
                    "severity": "info",
                    "title": f"{idle_vehicle_count} vehicle(s) still idle",
                    "description": "Vehicles exist in the fleet but are not linked to upcoming assignments.",
                    "action_to": "/company/schedule",
                    "action_label": "Review assignments",
                }
            )
        if routes_without_shops_count:
            alerts.append(
                {
                    "id": "routes-without-shops",
                    "severity": "warning",
                    "title": f"{routes_without_shops_count} route(s) missing stops",
                    "description": "These routes will not create meaningful deliveries until shops are added.",
                    "action_to": "/company/routes",
                    "action_label": "Update routes",
                }
            )
        if product_counts["zero_stock"]:
            alerts.append(
                {
                    "id": "zero-stock-products",
                    "severity": "critical",
                    "title": f"{product_counts['zero_stock']} product(s) out of stock",
                    "description": "Products with zero inventory can block shop fulfillment and route planning.",
                    "action_to": "/company/products",
                    "action_label": "Restock products",
                }
            )
        if assignment_counts["overdue"]:
            alerts.append(
                {
                    "id": "overdue-assignments",
                    "severity": "critical",
                    "title": f"{assignment_counts['overdue']} assignment(s) overdue",
                    "description": "These assignments are still marked assigned even though their start time has already passed.",
                    "action_to": "/company/schedule",
                    "action_label": "Resolve delays",
                }
            )

        payload = {
            "header": {
                "company_name": request.user.company.name if request.user.company else "Company",
                "generated_at": now.isoformat(),
            },
            "kpis": {
                "drivers": driver_counts["total"] or 0,
                "available_drivers": driver_counts["available"] or 0,
                "vehicles": vehicle_counts["total"] or 0,
                "available_vehicles": vehicle_counts["available"] or 0,
                "assignments_today": assignment_counts["today"] or 0,
                "active_runs": run_counts["active"] or 0,
                "completed_today": run_counts["completed_today"] or 0,
                "shops": shop_counts["total"] or 0,
                "products": product_counts["total"] or 0,
                "routes": route_counts["total"] or 0,
                "alerts": len(alerts),
            },
            "resources": {
                "drivers": {
                    "available": driver_counts["available"] or 0,
                    "in_route": driver_counts["in_route"] or 0,
                    "on_leave": driver_counts["on_leave"] or 0,
                    "unassigned": unassigned_driver_count,
                },
                "vehicles": {
                    "available": vehicle_counts["available"] or 0,
                    "on_route": vehicle_counts["on_route"] or 0,
                    "renovation": vehicle_counts["renovation"] or 0,
                    "idle": idle_vehicle_count,
                },
                "inventory": {
                    "low_stock": product_counts["low_stock"] or 0,
                    "zero_stock": product_counts["zero_stock"] or 0,
                },
                "network": {
                    "shops_without_route": shop_counts["without_route"] or 0,
                    "routes_without_shops": routes_without_shops_count,
                },
            },
            "assignment_status": assignment_status,
            "trend": trend,
            "operations": {
                "active_assignments": active_assignment_rows,
                "upcoming_assignments": upcoming_assignment_rows,
                "recent_activity": recent_assignment_rows,
            },
            "alerts": alerts,
        }
        cache.set(cache_key, payload, timeout=self.cache_timeout_seconds)
        return self.success_response(data=payload, message="Dashboard overview loaded.")
