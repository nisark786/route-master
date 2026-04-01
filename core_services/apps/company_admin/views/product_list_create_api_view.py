from django.core.cache import cache
from django.db import IntegrityError
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.company_admin.models import Product
from apps.company_admin.serializers import ProductSerializer
from apps.company_admin.services.cache import company_collection_cache_key

from .base import CompanyAdminAPIView


class ProductListCreateAPIView(CompanyAdminAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    required_permission_map = {
        "GET": "product.view",
        "POST": "product.create",
    }

    @swagger_auto_schema(
        tags=["Company Admin Products"],
        operation_summary="List products",
        operation_description="List all products belonging to the authenticated company admin.",
        responses={200: "Products loaded", 401: "Unauthorized", 403: "Forbidden"},
    )
    def get(self, request):
        cache_key = company_collection_cache_key(request.user.company_id, "products")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        queryset = Product.objects.filter(company_id=request.user.company_id).only(
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
        )
        payload = ProductSerializer(queryset, many=True, context={"request": request}).data
        cache.set(cache_key, payload, timeout=120)
        return Response(payload, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin Products"],
        operation_summary="Create product",
        operation_description="Create a product for the authenticated company admin.",
        request_body=ProductSerializer,
        responses={201: "Product created", 400: "Validation error", 401: "Unauthorized", 403: "Forbidden"},
    )
    def post(self, request):
        serializer = ProductSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            product = serializer.save(company_id=request.user.company_id)
        except IntegrityError:
            raise ValidationError({"name": ["A product with this name already exists."]})
        payload = ProductSerializer(product, context={"request": request}).data
        payload["message"] = "Product created successfully."
        return Response(payload, status=status.HTTP_201_CREATED)
