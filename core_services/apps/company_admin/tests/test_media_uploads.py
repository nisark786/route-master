import pytest
from rest_framework.exceptions import ValidationError

from apps.company_admin.services.media_uploads import (
    build_company_media_key,
    build_media_asset_url,
    build_storage_object_key,
    delete_media_asset,
    normalize_media_name,
)


@pytest.mark.django_db
def test_build_company_media_key_generates_safe_prefixed_key(company):
    key = build_company_media_key(
        company_id=company.id,
        kind="product",
        file_name="Fancy Product Image!!.PNG",
    )

    assert key.startswith(f"products/company-{company.id}/")
    assert key.endswith(".png")
    assert "fancy-product-image" in key


@pytest.mark.django_db
def test_build_company_media_key_rejects_unsupported_extension(company):
    with pytest.raises(ValidationError):
        build_company_media_key(company_id=company.id, kind="shop", file_name="malware.exe")


def test_build_storage_object_key_applies_media_prefix(settings):
    settings.AWS_S3_MEDIA_PREFIX = "media"

    assert build_storage_object_key("products/demo.png") == "media/products/demo.png"


def test_build_media_asset_url_uses_custom_domain_when_configured(settings):
    settings.USE_S3_MEDIA = True
    settings.AWS_S3_CUSTOM_DOMAIN = "cdn.example.com"
    settings.AWS_STORAGE_BUCKET_NAME = "bucket"
    settings.AWS_S3_REGION_NAME = "ap-south-1"

    url = build_media_asset_url("products/demo image.png")

    assert url == "https://cdn.example.com/products/demo%20image.png"


def test_normalize_media_name_strips_prefix(settings):
    settings.AWS_S3_MEDIA_PREFIX = "media"

    assert normalize_media_name("media/products/demo.png") == "products/demo.png"


def test_delete_media_asset_deletes_normalized_name(monkeypatch, settings):
    settings.AWS_S3_MEDIA_PREFIX = "media"
    deleted = {}

    def fake_delete(name):
        deleted["name"] = name

    monkeypatch.setattr("apps.company_admin.services.media_uploads.default_storage.delete", fake_delete)

    result = delete_media_asset("media/products/demo.png")

    assert result is True
    assert deleted["name"] == "products/demo.png"
