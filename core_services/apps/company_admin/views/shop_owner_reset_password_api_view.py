from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.company_admin.models import Shop
from apps.company_admin.serializers import TemporaryPasswordResetSerializer

from .base import CompanyAdminAPIView


class ShopOwnerResetPasswordAPIView(CompanyAdminAPIView):
    required_permission = "shop.reset_password"

    def _get_shop(self, company_id, shop_id):
        shop = Shop.objects.filter(company_id=company_id, id=shop_id).select_related("owner_user").first()
        if not shop:
            raise NotFound("Shop not found.")
        return shop

    @swagger_auto_schema(
        tags=["Company Admin Shops"],
        operation_summary="Reset shop owner temporary password",
        manual_parameters=[openapi.Parameter("shop_id", openapi.IN_PATH, type=openapi.TYPE_STRING, required=True)],
        request_body=TemporaryPasswordResetSerializer,
        responses={200: "Password reset"},
    )
    def post(self, request, shop_id):
        shop = self._get_shop(request.user.company_id, shop_id)
        if not shop.owner_user:
            raise ValidationError({"owner_user": ["Shop owner account not created for this shop."]})

        serializer = TemporaryPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        temporary_password = serializer.validated_data["temporary_password"].strip()
        shop.owner_user.set_password(temporary_password)
        shop.owner_user.must_change_password = True
        shop.owner_user.save(update_fields=["password", "must_change_password"])

        return Response(
            {
                "shop_id": str(shop.id),
                "mobile_number": shop.owner_user.mobile_number,
                "must_change_password": True,
                "message": "Shop owner temporary password reset successfully.",
            },
            status=status.HTTP_200_OK,
        )
