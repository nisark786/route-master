from django.db import IntegrityError
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.company_admin.models import Product
from apps.company_admin.serializers import ProductSerializer
from apps.company_admin.services import delete_media_asset

from .base import CompanyAdminAPIView


class ProductDetailAPIView(CompanyAdminAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    required_permission_map = {
        "GET": "product.view",
        "PATCH": "product.update",
        "DELETE": "product.delete",
    }

    def _get_product(self, company_id, product_id):
        product = Product.objects.filter(id=product_id, company_id=company_id).only(
            "id",
            "company_id",
            "name",
            "image",
            "quantity_count",
            "rate",
            "description",
            "shelf_life",
            "created_at",
            "updated_at",
        ).first()
        if not product:
            raise NotFound("Product not found.")
        return product

    @swagger_auto_schema(
        tags=["Company Admin Products"],
        operation_summary="Get product details",
        manual_parameters=[
            openapi.Parameter(
                "product_id",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            )
        ],
        responses={200: "Product loaded", 404: "Product not found"},
    )
    def get(self, request, product_id):
        product = self._get_product(request.user.company_id, product_id)
        return Response(ProductSerializer(product, context={"request": request}).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin Products"],
        operation_summary="Update product",
        manual_parameters=[
            openapi.Parameter(
                "product_id",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            )
        ],
        request_body=ProductSerializer,
        responses={200: "Product updated", 400: "Validation error", 404: "Product not found"},
    )
    def patch(self, request, product_id):
        product = self._get_product(request.user.company_id, product_id)
        previous_image_name = product.image.name if product.image else ""
        serializer = ProductSerializer(product, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            updated_product = serializer.save()
        except IntegrityError:
            raise ValidationError({"name": ["A product with this name already exists."]})
        new_image_name = updated_product.image.name if updated_product.image else ""
        if previous_image_name and previous_image_name != new_image_name:
            delete_media_asset(previous_image_name)
        payload = ProductSerializer(updated_product, context={"request": request}).data
        payload["message"] = "Product updated successfully."
        return Response(payload, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin Products"],
        operation_summary="Delete product",
        manual_parameters=[
            openapi.Parameter(
                "product_id",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            )
        ],
        responses={204: "Product deleted", 404: "Product not found"},
    )
    def delete(self, request, product_id):
        product = self._get_product(request.user.company_id, product_id)
        image_name = product.image.name if product.image else ""
        product.delete()
        if image_name:
            delete_media_asset(image_name)
        return Response({"message": "Product deleted successfully."}, status=status.HTTP_200_OK)
