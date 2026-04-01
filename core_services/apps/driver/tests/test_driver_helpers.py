import pytest
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.company_admin.models import RouteShop, Shop
from apps.driver.models import DriverRouteRun
from apps.driver.views.helpers import (
    build_whatsapp_url,
    ensure_stop_is_current_pending,
    get_assignment_for_driver,
    get_driver_for_user,
    get_or_create_run_for_assignment,
)


@pytest.mark.django_db
def test_get_driver_for_user_returns_driver_profile(driver_user, driver_profile):
    assert get_driver_for_user(driver_user) == driver_profile


@pytest.mark.django_db
def test_get_driver_for_user_raises_not_found_for_non_driver(company_admin_user):
    with pytest.raises(NotFound):
        get_driver_for_user(company_admin_user)


@pytest.mark.django_db
def test_get_assignment_for_driver_restricts_to_driver(driver_profile, driver_assignment):
    assert get_assignment_for_driver(driver_profile, driver_assignment.id) == driver_assignment


@pytest.mark.django_db
def test_get_or_create_run_for_assignment_creates_run_and_stops(
    company,
    driver_profile,
    driver_assignment,
    route,
    route_shop,
):
    second_shop = Shop.objects.create(
        company=company,
        name="Second Shop",
        owner_name="Second Owner",
        owner_mobile_number="9000000011",
        location="Town",
        location_display_name="Town Center",
        latitude="12.971700",
        longitude="77.594700",
        address="Other Street",
        landmark="Near Park",
    )
    RouteShop.objects.create(route=route, shop=second_shop, position=2)

    run, created = get_or_create_run_for_assignment(driver_assignment)

    driver_profile.refresh_from_db()
    assert created is True
    assert run.status == DriverRouteRun.STATUS_IN_PROGRESS
    assert driver_profile.status == driver_profile.STATUS_IN_ROUTE
    assert run.stops.count() == 2
    assert list(run.stops.values_list("position", flat=True)) == [1, 2]


@pytest.mark.django_db
def test_get_or_create_run_for_assignment_returns_existing_run(driver_assignment, route_shop):
    first_run, created = get_or_create_run_for_assignment(driver_assignment)
    second_run, second_created = get_or_create_run_for_assignment(driver_assignment)

    assert created is True
    assert second_created is False
    assert second_run.id == first_run.id


@pytest.mark.django_db
def test_get_or_create_run_for_assignment_rejects_cancelled_assignment(driver_assignment):
    driver_assignment.status = driver_assignment.STATUS_CANCELLED
    driver_assignment.save(update_fields=["status"])

    with pytest.raises(ValidationError):
        get_or_create_run_for_assignment(driver_assignment)


@pytest.mark.django_db
def test_ensure_stop_is_current_pending_rejects_out_of_order_stop(
    company,
    driver_assignment,
    route,
    route_shop,
):
    second_shop = Shop.objects.create(
        company=company,
        name="Second Shop",
        owner_name="Second Owner",
        owner_mobile_number="9000000012",
        location="Town",
        location_display_name="Town Center",
        latitude="12.971700",
        longitude="77.594700",
        address="Other Street",
        landmark="Near Park",
    )
    RouteShop.objects.create(route=route, shop=second_shop, position=2)
    run, _ = get_or_create_run_for_assignment(driver_assignment)
    second_stop = run.stops.get(position=2)

    with pytest.raises(ValidationError):
        ensure_stop_is_current_pending(run, second_stop)


def test_build_whatsapp_url_normalizes_number_and_encodes_message():
    url = build_whatsapp_url("+91 98765-43210", "Hello Driver")

    assert url == "https://wa.me/919876543210?text=Hello%20Driver"
