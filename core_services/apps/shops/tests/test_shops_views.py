import pytest
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework.test import APIRequestFactory

from apps.driver.models import DriverRouteRun, DriverRunStop
from apps.shops.views import _build_invoice_url, _serialize_stop


@pytest.mark.django_db
def test_build_invoice_url_returns_empty_string_without_invoice(route_shop, driver_profile, driver_assignment, vehicle, route):
    run = DriverRouteRun.objects.create(
        assignment=driver_assignment,
        driver=driver_profile,
        route=route,
        vehicle=vehicle,
        status=DriverRouteRun.STATUS_IN_PROGRESS,
        started_at=timezone.now(),
    )
    stop = DriverRunStop.objects.create(
        run=run,
        route_shop=route_shop,
        shop=route_shop.shop,
        position=1,
    )
    request = APIRequestFactory().get("/api/core/shops/dashboard/")

    assert _build_invoice_url(request, stop) == ""


@pytest.mark.django_db
def test_serialize_stop_includes_invoice_and_route_context(route_shop, driver_profile, driver_assignment, vehicle, route, settings):
    settings.MEDIA_URL = "/media/"
    run = DriverRouteRun.objects.create(
        assignment=driver_assignment,
        driver=driver_profile,
        route=route,
        vehicle=vehicle,
        status=DriverRouteRun.STATUS_COMPLETED,
        started_at=timezone.now(),
    )
    stop = DriverRunStop.objects.create(
        run=run,
        route_shop=route_shop,
        shop=route_shop.shop,
        position=1,
        status=DriverRunStop.STATUS_COMPLETED,
        invoice_number="INV-001",
        invoice_total="120.00",
    )
    stop.invoice_file.save("invoice.txt", ContentFile(b"demo invoice"), save=True)
    request = APIRequestFactory().get("/api/core/shops/dashboard/")

    payload = _serialize_stop(request, stop)

    assert payload["shop_name"] == route_shop.shop.name
    assert payload["route_name"] == route.route_name
    assert payload["invoice_number"] == "INV-001"
    assert "/invoices/" in payload["invoice_url"]
