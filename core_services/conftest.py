import os

import pytest
import psycopg2
from psycopg2 import sql
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient

from apps.authentication.models import User
from apps.company.models import Company
from apps.authentication.services import generate_tokens_for_user
from apps.billing.models import SubscriptionPlan
from apps.company_admin.models import Driver, DriverAssignment, Product, Route, RouteShop, Shop, Vehicle


def _test_database_name():
    db_name = os.environ.get("DB_NAME", "route_db")
    return f"test_{db_name}"


def _cleanup_lingering_test_database():
    connection_kwargs = {
        "dbname": os.environ.get("DB_ADMIN_DB", "postgres"),
        "user": os.environ.get("DB_USER", "postgres"),
        "password": os.environ.get("DB_PASSWORD", ""),
        "host": os.environ.get("DB_HOST", "localhost"),
        "port": os.environ.get("DB_PORT", "5432"),
    }
    test_db_name = _test_database_name()

    admin_connection = psycopg2.connect(**connection_kwargs)
    admin_connection.autocommit = True
    try:
        with admin_connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT pg_terminate_backend(pid)
                FROM pg_stat_activity
                WHERE datname = %s AND pid <> pg_backend_pid()
                """,
                [test_db_name],
            )
            cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(sql.Identifier(test_db_name)))
    finally:
        admin_connection.close()


def pytest_sessionstart(session):
    _cleanup_lingering_test_database()


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def auth_client():
    def _build(user):
        client = APIClient()
        tokens = generate_tokens_for_user(user)
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        return client

    return _build


@pytest.fixture
def company(db):
    return Company.objects.create(
        name="Test Company",
        official_email="company@example.com",
        phone="9999999999",
    )


@pytest.fixture
def company_admin_user(db, company):
    return User.objects.create_user(
        email="admin@example.com",
        password="StrongPass123",
        role="COMPANY_ADMIN",
        company=company,
        mobile_number="9876543210",
        must_change_password=False,
    )


@pytest.fixture
def super_admin_user(db):
    return User.objects.create_superuser(
        email="superadmin@example.com",
        password="StrongPass123",
        role="SUPER_ADMIN",
    )


@pytest.fixture
def driver_user(db, company):
    return User.objects.create_user(
        email="driver@example.com",
        password="StrongPass123",
        role="DRIVER",
        company=company,
        mobile_number="9000000001",
        must_change_password=False,
    )


@pytest.fixture
def shop_owner_user(db, company):
    return User.objects.create_user(
        email="shopowner@example.com",
        password="StrongPass123",
        role="SHOP_OWNER",
        company=company,
        mobile_number="9000000002",
        must_change_password=False,
    )


@pytest.fixture
def first_login_user(db, company):
    return User.objects.create_user(
        email="firstlogin@example.com",
        password="TempPass123",
        role="COMPANY_ADMIN",
        company=company,
        mobile_number="9123456789",
        must_change_password=True,
    )


@pytest.fixture
def subscription_plan(db):
    return SubscriptionPlan.objects.create(
        code="basic",
        name="Basic",
        price="999.00",
        duration_days=30,
        features=["core"],
        is_active=True,
    )


@pytest.fixture
def vehicle(db, company):
    return Vehicle.objects.create(
        company=company,
        name="Test Van",
        number_plate="MH12AB1234",
        fuel_percentage=80,
    )


@pytest.fixture
def route(db, company):
    return Route.objects.create(
        company=company,
        route_name="Morning Route",
        start_point="Warehouse",
        end_point="Market",
    )


@pytest.fixture
def product(db, company):
    return Product.objects.create(
        company=company,
        name="Test Product",
        quantity_count=10,
        rate="150.00",
        description="Dashboard test product",
        shelf_life="3 months",
    )


@pytest.fixture
def shop(db, company, shop_owner_user):
    return Shop.objects.create(
        company=company,
        name="Demo Shop",
        owner_name="Shop Owner",
        owner_mobile_number=shop_owner_user.mobile_number,
        owner_user=shop_owner_user,
        location="Town",
        location_display_name="Town Center",
        latitude="12.971600",
        longitude="77.594600",
        address="Main Street",
        landmark="Near Circle",
    )


@pytest.fixture
def route_shop(db, route, shop):
    return RouteShop.objects.create(route=route, shop=shop, position=1)


@pytest.fixture
def driver_profile(db, driver_user):
    return Driver.objects.create(
        user=driver_user,
        name="Test Driver",
        age=30,
    )


@pytest.fixture
def driver_assignment(db, driver_profile, route, vehicle):
    return DriverAssignment.objects.create(
        driver=driver_profile,
        route=route,
        vehicle=vehicle,
        scheduled_at=timezone.now(),
        notes="Test assignment",
    )
