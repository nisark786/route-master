from django.core.cache import cache
from django.db import IntegrityError
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.company_admin.models import Vehicle
from apps.company_admin.serializers import VehicleSerializer
from apps.company_admin.services.cache import company_collection_cache_key

from .base import CompanyAdminAPIView


class VehicleListCreateAPIView(CompanyAdminAPIView):
    required_permission_map = {
        "GET": "vehicle.view",
        "POST": "vehicle.create",
    }
    @swagger_auto_schema(
        tags=["Company Admin"],
        operation_summary="List vehicles",
        operation_description="List all vehicles belonging to the authenticated company admin.",
        responses={200: "Vehicles loaded", 401: "Unauthorized", 403: "Forbidden"},
    )
    def get(self, request):
        cache_key = company_collection_cache_key(request.user.company_id, "vehicles")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        payload = [
            {
                **item,
                "id": str(item["id"]),
            }
            for item in (
            Vehicle.objects.filter(company_id=request.user.company_id)
            .values("id", "name", "number_plate", "status", "created_at", "updated_at")
            )
        ]
        cache.set(cache_key, payload, timeout=120)
        return Response(payload, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin"],
        operation_summary="Create vehicle",
        operation_description="Create a vehicle for the authenticated company admin.",
        request_body=VehicleSerializer,
        responses={201: "Vehicle created", 400: "Validation error", 401: "Unauthorized", 403: "Forbidden"},
    )
    def post(self, request):
        serializer = VehicleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            vehicle = serializer.save(company_id=request.user.company_id)
        except IntegrityError:
            raise ValidationError({"number_plate": ["A vehicle with this number plate already exists."]})
        payload = VehicleSerializer(vehicle).data
        payload["message"] = "Vehicle created successfully."
        return Response(payload, status=status.HTTP_201_CREATED)
