import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIRequestFactory

from apps.company_admin.serializers import ProductSerializer, ShopSerializer


def _request_for_user(user):
    request = APIRequestFactory().post("/api/core/company-admin/test/")
    request.user = user
    return request


@pytest.mark.django_db
def test_product_serializer_validates_and_saves_image_key(company_admin_user, company):
    serializer = ProductSerializer(
        data={
            "name": "  Apples  ",
            "image_key": f"products/company-{company.id}/demo.png",
            "quantity_count": 5,
            "rate": "12.50",
            "description": "  Fresh  ",
            "shelf_life": "  3 days  ",
        },
        context={"request": _request_for_user(company_admin_user)},
    )

    assert serializer.is_valid(), serializer.errors
    product = serializer.save(company=company)

    assert product.name == "Apples"
    assert product.description == "Fresh"
    assert product.shelf_life == "3 days"
    assert product.image.name == f"products/company-{company.id}/demo.png"


@pytest.mark.django_db
def test_product_serializer_rejects_wrong_company_image_key(company_admin_user):
    serializer = ProductSerializer(
        data={
            "name": "Apples",
            "image_key": "products/company-wrong/demo.png",
            "quantity_count": 1,
            "rate": "1.00",
            "description": "",
            "shelf_life": "",
        },
        context={"request": _request_for_user(company_admin_user)},
    )

    assert not serializer.is_valid()
    assert "image_key" in serializer.errors


@pytest.mark.django_db
def test_product_serializer_rejects_invalid_file_upload():
    upload = SimpleUploadedFile("notes.txt", b"hello", content_type="text/plain")
    serializer = ProductSerializer(
        data={
            "name": "Apples",
            "image": upload,
            "quantity_count": 1,
            "rate": "1.00",
            "description": "",
            "shelf_life": "",
        }
    )

    assert not serializer.is_valid()
    assert "image" in serializer.errors


@pytest.mark.django_db
def test_shop_serializer_normalizes_fields_builds_point_and_saves_image_key(company_admin_user, company):
    serializer = ShopSerializer(
        data={
            "name": "  Demo Shop ",
            "location": " City Center ",
            "location_display_name": " Main Hub ",
            "latitude": "12.9716",
            "longitude": "77.5946",
            "owner_name": " Shop Owner ",
            "owner_mobile_number": " 98765-43210 ",
            "image_key": f"shops/company-{company.id}/shop.png",
            "address": " Main Street ",
            "landmark": " Near Circle ",
        },
        context={"request": _request_for_user(company_admin_user)},
    )

    assert serializer.is_valid(), serializer.errors
    shop = serializer.save(company=company)

    assert shop.name == "Demo Shop"
    assert shop.owner_name == "Shop Owner"
    assert shop.owner_mobile_number == "9876543210"
    assert shop.point.x == pytest.approx(77.5946)
    assert shop.point.y == pytest.approx(12.9716)
    assert shop.image.name == f"shops/company-{company.id}/shop.png"


@pytest.mark.django_db
def test_shop_serializer_requires_latitude_and_longitude(company_admin_user):
    serializer = ShopSerializer(
        data={
            "name": "Demo Shop",
            "location": "City Center",
            "location_display_name": "Main Hub",
            "owner_name": "Shop Owner",
            "owner_mobile_number": "9876543210",
            "address": "Main Street",
            "landmark": "Near Circle",
        },
        context={"request": _request_for_user(company_admin_user)},
    )

    assert not serializer.is_valid()
    assert "latitude" in serializer.errors
    assert "longitude" in serializer.errors


@pytest.mark.django_db
def test_shop_serializer_rejects_wrong_company_image_key(company_admin_user):
    serializer = ShopSerializer(
        data={
            "name": "Demo Shop",
            "location": "City Center",
            "location_display_name": "Main Hub",
            "latitude": "12.9716",
            "longitude": "77.5946",
            "owner_name": "Shop Owner",
            "owner_mobile_number": "9876543210",
            "image_key": "shops/company-wrong/shop.png",
            "address": "Main Street",
            "landmark": "Near Circle",
        },
        context={"request": _request_for_user(company_admin_user)},
    )

    assert not serializer.is_valid()
    assert "image_key" in serializer.errors
