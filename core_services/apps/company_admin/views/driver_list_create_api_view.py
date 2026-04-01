from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db import models
from django.db.models import Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.authentication.models import User
from apps.company_admin.models import Driver
from apps.company_admin.serializers import DriverListQuerySerializer, DriverSerializer
from apps.company_admin.services.cache import company_collection_cache_key

from .base import CompanyAdminAPIView


class DriverListCreateAPIView(CompanyAdminAPIView):
    required_permission_map = {
        "GET": "driver.view",
        "POST": "driver.create",
    }

    def _build_driver_email(self, company_id, mobile_number):
        sanitized = "".join(ch for ch in mobile_number if ch.isdigit())
        return f"driver.{sanitized}.{str(company_id)[:8]}@local.routemaster"

    @swagger_auto_schema(
        tags=["Company Admin Drivers"],
        operation_summary="List drivers",
        manual_parameters=[openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING)],
        responses={200: "Drivers loaded"},
    )
    def get(self, request):
        query_serializer = DriverListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        search = query_serializer.validated_data["search"].strip()
        cache_key = company_collection_cache_key(request.user.company_id, "drivers", search or "all")
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        payload = [
            {
                **item,
                "id": str(item["id"]),
                "user_id": str(item["user_id"]),
            }
            for item in (
            Driver.objects.filter(user__company_id=request.user.company_id)
            .values(
                "id",
                "user_id",
                "name",
                "age",
                "status",
                "created_at",
                "updated_at",
                mobile_number=models.F("user__mobile_number"),
            )
            .order_by("-created_at")
            )
        ]
        if search:
            payload = [
                {
                    **item,
                    "id": str(item["id"]),
                    "user_id": str(item["user_id"]),
                }
                for item in (
                Driver.objects.filter(user__company_id=request.user.company_id)
                .filter(Q(name__icontains=search) | Q(user__mobile_number__icontains=search))
                .values(
                    "id",
                    "user_id",
                    "name",
                    "age",
                    "status",
                    "created_at",
                    "updated_at",
                    mobile_number=models.F("user__mobile_number"),
                )
                .order_by("-created_at")
                )
            ]
        cache.set(cache_key, payload, timeout=120)
        return Response(payload, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin Drivers"],
        operation_summary="Create driver",
        request_body=DriverSerializer,
        responses={201: "Driver created"},
    )
    def post(self, request):
        serializer = DriverSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        temporary_password = (request.data.get("temporary_password") or "").strip()
        if not temporary_password:
            raise ValidationError({"temporary_password": ["Temporary password is required."]})
        if len(temporary_password) < 8:
            raise ValidationError({"temporary_password": ["Temporary password must be at least 8 characters."]})
        mobile_number = serializer.validated_data["user"]["mobile_number"]
        try:
            with transaction.atomic():
                user = User.objects.create(
                    email=self._build_driver_email(request.user.company_id, mobile_number),
                    mobile_number=mobile_number,
                    role="DRIVER",
                    company_id=request.user.company_id,
                    must_change_password=True,
                    is_active=True,
                )
                user.set_password(temporary_password)
                user.save(update_fields=["password"])
                driver = serializer.save(user=user)
        except IntegrityError:
            raise ValidationError({"mobile_number": ["A driver with this mobile number already exists."]})
        payload = DriverSerializer(driver).data
        payload["must_change_password"] = True
        payload["message"] = "Driver account created successfully."
        return Response(payload, status=status.HTTP_201_CREATED)
