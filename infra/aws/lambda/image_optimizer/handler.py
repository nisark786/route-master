import io
import logging
import os
from urllib.parse import unquote_plus

import boto3
from PIL import Image, ImageOps


logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client("s3")

MAX_DIMENSION = int(os.getenv("MAX_DIMENSION", "1600"))
JPEG_QUALITY = int(os.getenv("JPEG_QUALITY", "82"))
WEBP_QUALITY = int(os.getenv("WEBP_QUALITY", "80"))
PNG_MAX_COLORS = int(os.getenv("PNG_MAX_COLORS", "256"))
OPTIMIZED_METADATA_KEY = "optimized"
SUPPORTED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}


def lambda_handler(event, context):
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        try:
            process_object(bucket, key)
        except Exception as exc:
            logger.exception("Failed to process %s/%s: %s", bucket, key, exc)
            raise

    return {"statusCode": 200}


def process_object(bucket, key):
    if not key.startswith("media/products/") and not key.startswith("media/shops/"):
        logger.info("Skipping non-product/shop object: %s", key)
        return

    head = s3.head_object(Bucket=bucket, Key=key)
    metadata = {k.lower(): v for k, v in (head.get("Metadata") or {}).items()}
    if metadata.get(OPTIMIZED_METADATA_KEY) == "true":
        logger.info("Skipping already optimized object: %s", key)
        return

    content_type = (head.get("ContentType") or "").lower()
    if content_type not in SUPPORTED_CONTENT_TYPES:
        logger.info("Skipping unsupported content type %s for %s", content_type, key)
        return

    source = s3.get_object(Bucket=bucket, Key=key)
    source_bytes = source["Body"].read()
    optimized_bytes, output_content_type = optimize_image(source_bytes, content_type)

    if len(optimized_bytes) >= len(source_bytes):
        logger.info("Optimized image is not smaller; keeping original bytes for %s", key)
        optimized_bytes = source_bytes
        output_content_type = content_type

    metadata[OPTIMIZED_METADATA_KEY] = "true"
    s3.put_object(
        Bucket=bucket,
        Key=key,
        Body=optimized_bytes,
        ContentType=output_content_type,
        Metadata=metadata,
        CacheControl="public, max-age=31536000, immutable",
    )
    logger.info("Optimized %s", key)


def optimize_image(source_bytes, content_type):
    image = Image.open(io.BytesIO(source_bytes))
    image = ImageOps.exif_transpose(image)

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGBA" if "A" in image.getbands() else "RGB")

    image.thumbnail((MAX_DIMENSION, MAX_DIMENSION))

    output = io.BytesIO()
    if content_type in {"image/jpeg", "image/jpg"}:
        image = image.convert("RGB")
        image.save(output, format="JPEG", optimize=True, quality=JPEG_QUALITY, progressive=True)
        return output.getvalue(), "image/jpeg"

    if content_type == "image/png":
        image = optimize_png(image)
        image.save(output, format="PNG", optimize=True, compress_level=9)
        return output.getvalue(), "image/png"

    image.save(output, format="WEBP", quality=WEBP_QUALITY, method=6)
    return output.getvalue(), "image/webp"


def optimize_png(image):
    if "A" in image.getbands():
        rgba = image.convert("RGBA")
        return rgba.quantize(colors=PNG_MAX_COLORS, method=Image.Quantize.FASTOCTREE)

    rgb = image.convert("RGB")
    return rgb.quantize(colors=PNG_MAX_COLORS, method=Image.Quantize.MEDIANCUT)
