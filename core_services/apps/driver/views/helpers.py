from urllib.parse import quote

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.company_admin.models import Driver, DriverAssignment
from apps.driver.models import DriverRouteRun, DriverRunStop


def get_driver_for_user(user):
    driver = Driver.objects.filter(user_id=user.id, user__company_id=user.company_id).first()
    if not driver:
        raise NotFound("Driver profile not found.")
    return driver


def get_assignment_for_driver(driver, assignment_id):
    assignment = (
        DriverAssignment.objects.filter(id=assignment_id, driver_id=driver.id)
        .select_related("route", "vehicle", "driver")
        .first()
    )
    if not assignment:
        raise NotFound("Assignment not found.")
    return assignment


def get_or_create_run_for_assignment(assignment):
    if assignment.status == DriverAssignment.STATUS_CANCELLED:
        raise ValidationError({"assignment": ["This assignment is cancelled and cannot be started."]})

    if assignment.status == DriverAssignment.STATUS_COMPLETED:
        raise ValidationError({"assignment": ["This assignment is already completed."]})

    run = (
        DriverRouteRun.objects.filter(assignment_id=assignment.id)
        .select_related("assignment", "route", "vehicle", "driver")
        .first()
    )
    if run:
        return run, False

    route_shops = assignment.route.route_shops.select_related("shop").all().order_by("position")
    if not route_shops.exists():
        raise ValidationError({"assignment": ["Route has no shops to execute."]})

    with transaction.atomic():
        existing_active = DriverRouteRun.objects.select_for_update().filter(
            driver_id=assignment.driver_id,
            status=DriverRouteRun.STATUS_IN_PROGRESS,
        )
        if existing_active.exists():
            raise ValidationError({"assignment": ["Finish current route before starting another assignment."]})

        run = DriverRouteRun.objects.create(
            assignment=assignment,
            driver=assignment.driver,
            route=assignment.route,
            vehicle=assignment.vehicle,
            status=DriverRouteRun.STATUS_IN_PROGRESS,
            started_at=timezone.now(),
        )
        DriverRunStop.objects.bulk_create(
            [
                DriverRunStop(
                    run=run,
                    route_shop=route_shop,
                    shop=route_shop.shop,
                    position=route_shop.position,
                )
                for route_shop in route_shops
            ]
        )

        assignment.status = DriverAssignment.STATUS_IN_ROUTE
        assignment.save(update_fields=["status", "updated_at"])

        assignment.driver.status = "IN_ROUTE"
        assignment.driver.save(update_fields=["status", "updated_at"])

    run = (
        DriverRouteRun.objects.filter(id=run.id)
        .select_related("assignment", "route", "vehicle", "driver")
        .first()
    )
    return run, True


def get_run_for_driver(driver, assignment_id):
    run = (
        DriverRouteRun.objects.filter(assignment_id=assignment_id, driver_id=driver.id)
        .select_related("assignment", "route", "vehicle", "driver")
        .first()
    )
    if not run:
        raise NotFound("Route run not started for this assignment.")
    return run


def get_next_pending_stop(run):
    return run.stops.filter(status=DriverRunStop.STATUS_PENDING).order_by("position").first()


def get_stop_for_run(run, shop_id):
    stop = run.stops.select_related("shop", "route_shop").filter(shop_id=shop_id).first()
    if not stop:
        raise NotFound("Stop not found in this route.")
    return stop


def ensure_stop_is_current_pending(run, stop):
    next_pending = get_next_pending_stop(run)
    if not next_pending:
        raise ValidationError({"stop": ["All stops are already completed."]})
    if next_pending.id != stop.id:
        raise ValidationError({"stop": ["You must complete shops in route order."]})


def build_whatsapp_url(number, message):
    digits = "".join(ch for ch in (number or "") if ch.isdigit())
    if not digits:
        return ""
    return f"https://wa.me/{digits}?text={quote(message)}"
