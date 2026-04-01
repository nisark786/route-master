from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.db.models import Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response

from apps.authentication.models import User
from apps.company_admin.models import Shop
from apps.company_admin.pagination import ShopPageNumberPagination
from apps.company_admin.serializers import ShopListQuerySerializer, ShopSerializer
from apps.company_admin.services.cache import company_collection_cache_key

from .base import CompanyAdminAPIView


class ShopListCreateAPIView(CompanyAdminAPIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    required_permission_map = {
        "GET": "shop.view",
        "POST": "shop.create",
    }

    @swagger_auto_schema(
        tags=["Company Admin"],
        operation_summary="List shops",
        operation_description="List company shops with search by name/owner and page number pagination.",
        manual_parameters=[
            openapi.Parameter("search", openapi.IN_QUERY, type=openapi.TYPE_STRING),
            openapi.Parameter("page", openapi.IN_QUERY, type=openapi.TYPE_INTEGER),
        ],
        responses={200: "Shops loaded", 401: "Unauthorized", 403: "Forbidden"},
    )
    def get(self, request):
        query_serializer = ShopListQuerySerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        search = query_serializer.validated_data["search"].strip()
        page_number = request.query_params.get("page", "1")
        cache_key = company_collection_cache_key(request.user.company_id, "shops", search or "all", page_number)
        cached = cache.get(cache_key)
        if cached is not None:
            return Response(cached, status=status.HTTP_200_OK)

        shops = (
            Shop.objects.filter(company_id=request.user.company_id)
            .select_related("owner_user")
            .only(
                "id",
                "name",
                "location",
                "location_display_name",
                "latitude",
                "longitude",
                "point",
                "owner_name",
                "owner_mobile_number",
                "owner_user__id",
                "image",
                "address",
                "landmark",
                "created_at",
                "updated_at",
            )
            .order_by("-created_at")
        )
        if search:
            shops = shops.filter(Q(name__icontains=search) | Q(owner_name__icontains=search))

        paginator = ShopPageNumberPagination()
        page = paginator.paginate_queryset(shops, request, view=self)
        results = ShopSerializer(page, many=True, context={"request": request}).data

        payload = {
            "count": paginator.page.paginator.count,
            "page": paginator.page.number,
            "page_size": paginator.get_page_size(request),
            "total_pages": paginator.page.paginator.num_pages,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": results,
        }
        cache.set(cache_key, payload, timeout=120)
        return Response(payload, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin"],
        operation_summary="Create shop",
        operation_description="Create a shop under authenticated company admin.",
        request_body=ShopSerializer,
        responses={201: "Shop created", 400: "Validation error", 401: "Unauthorized", 403: "Forbidden"},
    )
    def post(self, request):
        serializer = ShopSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                shop = serializer.save(company_id=request.user.company_id)
                owner_mobile = serializer.validated_data.get("owner_mobile_number", "")
                if owner_mobile:
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
                    shop.owner_user = owner_user
                    shop.save(update_fields=["owner_user", "updated_at"])
        except IntegrityError:
            raise ValidationError({"name": ["A shop with same name/owner exists, or owner mobile already exists."]})

        response_data = ShopSerializer(shop, context={"request": request}).data
        response_data["message"] = "Shop created successfully."
        return Response(response_data, status=status.HTTP_201_CREATED)

    def _build_shop_owner_email(self, company_id, mobile_number):
        sanitized = "".join(ch for ch in mobile_number if ch.isdigit())
        return f"shop.{sanitized}.{str(company_id)[:8]}@local.routemaster"
