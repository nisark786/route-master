from django.db import IntegrityError, transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.authentication.models import User
from apps.company_admin.models import Shop
from apps.company_admin.serializers import ShopSerializer
from apps.company_admin.services import delete_media_asset

from .base import CompanyAdminAPIView


class ShopDetailAPIView(CompanyAdminAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    required_permission_map = {
        "GET": "shop.view",
        "PATCH": "shop.update",
        "DELETE": "shop.delete",
    }

    def _get_shop(self, company_id, shop_id):
        shop = (
            Shop.objects.filter(id=shop_id, company_id=company_id)
            .select_related("owner_user")
            .only(
                "id",
                "company_id",
                "name",
                "location",
                "location_display_name",
                "latitude",
                "longitude",
                "point",
                "owner_name",
                "owner_mobile_number",
                "owner_user__id",
                "owner_user__mobile_number",
                "image",
                "address",
                "landmark",
                "created_at",
                "updated_at",
            )
            .first()
        )
        if not shop:
            raise NotFound("Shop not found.")
        return shop

    @swagger_auto_schema(
        tags=["Company Admin"],
        operation_summary="Get shop detail",
        manual_parameters=[
            openapi.Parameter(
                "shop_id",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            )
        ],
        responses={200: "Shop loaded", 404: "Shop not found"},
    )
    def get(self, request, shop_id):
        shop = self._get_shop(request.user.company_id, shop_id)
        return Response(ShopSerializer(shop, context={"request": request}).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin"],
        operation_summary="Update shop",
        manual_parameters=[
            openapi.Parameter(
                "shop_id",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            )
        ],
        request_body=ShopSerializer,
        responses={200: "Shop updated", 400: "Validation error", 404: "Shop not found"},
    )
    def patch(self, request, shop_id):
        shop = self._get_shop(request.user.company_id, shop_id)
        previous_image_name = shop.image.name if shop.image else ""
        serializer = ShopSerializer(shop, data=request.data, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                updated_shop = serializer.save()
                owner_mobile = serializer.validated_data.get("owner_mobile_number")
                if owner_mobile is not None:
                    owner_mobile = owner_mobile.strip()
                    if owner_mobile:
                        if updated_shop.owner_user and updated_shop.owner_user.mobile_number != owner_mobile:
                            updated_shop.owner_user.delete()
                            updated_shop.owner_user = None
                        if not updated_shop.owner_user:
                            temporary_password = (request.data.get("temporary_password") or "").strip()
                            if not temporary_password:
                                raise ValidationError({"temporary_password": ["Temporary password is required when owner mobile is provided."]})
                            if len(temporary_password) < 8:
                                raise ValidationError({"temporary_password": ["Temporary password must be at least 8 characters."]})
                            owner_user = User.objects.create(
                                email=self._build_shop_owner_email(request.user.company_id, owner_mobile),
                                mobile_number=owner_mobile,
                                role="SHOP_OWNER",
                                company_id=request.user.company_id,
                                must_change_password=True,
                                is_active=True,
                            )
                            owner_user.set_password(temporary_password)
                            owner_user.save(update_fields=["password"])
                            updated_shop.owner_user = owner_user
                            updated_shop.save(update_fields=["owner_user", "updated_at"])
                        else:
                            updated_shop.owner_user.mobile_number = owner_mobile
                            updated_shop.owner_user.save(update_fields=["mobile_number"])
                    elif updated_shop.owner_user:
                        updated_shop.owner_user.delete()
                        updated_shop.owner_user = None
                        updated_shop.save(update_fields=["owner_user", "updated_at"])
        except IntegrityError:
            raise ValidationError({"name": ["Shop or owner details conflict with existing records."]})
        new_image_name = updated_shop.image.name if updated_shop.image else ""
        if previous_image_name and previous_image_name != new_image_name:
            delete_media_asset(previous_image_name)
        response_data = ShopSerializer(updated_shop, context={"request": request}).data
        response_data["message"] = "Shop updated successfully."
        return Response(response_data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin"],
        operation_summary="Delete shop",
        manual_parameters=[
            openapi.Parameter(
                "shop_id",
                openapi.IN_PATH,
                type=openapi.TYPE_STRING,
                format=openapi.FORMAT_UUID,
                required=True,
            )
        ],
        responses={200: "Shop deleted", 404: "Shop not found"},
    )
    def delete(self, request, shop_id):
        shop = self._get_shop(request.user.company_id, shop_id)
        image_name = shop.image.name if shop.image else ""
        owner_user = shop.owner_user
        shop.delete()
        if image_name:
            delete_media_asset(image_name)
        if owner_user:
            owner_user.delete()
        return Response({"message": "Shop deleted successfully."}, status=status.HTTP_200_OK)
    def _build_shop_owner_email(self, company_id, mobile_number):
        sanitized = "".join(ch for ch in mobile_number if ch.isdigit())
        return f"shop.{sanitized}.{str(company_id)[:8]}@local.routemaster"
