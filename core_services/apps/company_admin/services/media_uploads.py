import os
import uuid
from urllib.parse import quote

import boto3
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework.exceptions import ValidationError


ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def ensure_s3_media_enabled():
    if not settings.USE_S3_MEDIA:
        raise ValidationError({"storage": ["S3 media storage is not enabled. Set USE_S3_MEDIA=True."]})


def build_company_media_key(*, company_id, kind, file_name):
    base_name = os.path.basename(file_name or "upload")
    root, extension = os.path.splitext(base_name)
    normalized_extension = extension.lower()
    if normalized_extension not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError({"file_name": ["Allowed image types: jpg, jpeg, png, webp, gif."]})

    safe_root = "".join(ch if ch.isalnum() else "-" for ch in root).strip("-").lower() or "image"
    safe_root = safe_root[:24].strip("-") or "image"
    return f"{kind}s/company-{company_id}/{uuid.uuid4()}-{safe_root}{normalized_extension}"


def build_storage_object_key(relative_key):
    normalized_key = (relative_key or "").lstrip("/")
    media_prefix = (settings.AWS_S3_MEDIA_PREFIX or "").strip("/")
    if media_prefix:
        return f"{media_prefix}/{normalized_key}"
    return normalized_key


def generate_product_or_shop_upload_payload(*, company_id, kind, file_name, content_type):
    ensure_s3_media_enabled()

    relative_key = build_company_media_key(company_id=company_id, kind=kind, file_name=file_name)
    object_key = build_storage_object_key(relative_key)
    client = boto3.client("s3", region_name=settings.AWS_S3_REGION_NAME or None)
    upload_url = client.generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.AWS_STORAGE_BUCKET_NAME,
            "Key": object_key,
            "ContentType": content_type,
        },
        ExpiresIn=900,
    )
    return {
        "upload_url": upload_url,
        "method": "PUT",
        "headers": {"Content-Type": content_type},
        "object_key": relative_key,
        "asset_url": build_media_asset_url(relative_key),
    }


def build_media_asset_url(object_key):
    ensure_s3_media_enabled()
    normalized_key = object_key.lstrip("/")
    if settings.AWS_S3_CUSTOM_DOMAIN:
        return f"https://{settings.AWS_S3_CUSTOM_DOMAIN.rstrip('/')}/{quote(normalized_key)}"
    bucket = settings.AWS_STORAGE_BUCKET_NAME
    region = settings.AWS_S3_REGION_NAME
    if region:
        return f"https://{bucket}.s3.{region}.amazonaws.com/{quote(normalized_key)}"
    return f"https://{bucket}.s3.amazonaws.com/{quote(normalized_key)}"


def normalize_media_name(file_name):
    normalized_name = (file_name or "").strip().lstrip("/")
    media_prefix = (settings.AWS_S3_MEDIA_PREFIX or "").strip("/")
    if media_prefix and normalized_name.startswith(f"{media_prefix}/"):
        return normalized_name[len(media_prefix) + 1 :]
    return normalized_name


def delete_media_asset(file_name):
    normalized_name = normalize_media_name(file_name)
    if not normalized_name:
        return False
    try:
        default_storage.delete(normalized_name)
        return True
    except Exception:
        return False
