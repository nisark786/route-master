from drf_yasg.utils import swagger_auto_schema
from rest_framework import status

from apps.company_admin.serializers import MediaUploadRequestSerializer
from apps.company_admin.services.media_uploads import generate_product_or_shop_upload_payload

from .base import CompanyAdminAPIView


class MediaUploadPresignAPIView(CompanyAdminAPIView):
    required_permission_map = {
        "POST": "company_admin.access",
    }

    @swagger_auto_schema(
        tags=["Company Admin Media"],
        operation_summary="Create a presigned product/shop image upload URL",
        request_body=MediaUploadRequestSerializer,
        responses={200: "Upload URL created", 400: "Validation error", 401: "Unauthorized", 403: "Forbidden"},
    )
    def post(self, request):
        serializer = MediaUploadRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = generate_product_or_shop_upload_payload(
            company_id=request.user.company_id,
            kind=serializer.validated_data["kind"],
            file_name=serializer.validated_data["file_name"],
            content_type=serializer.validated_data["content_type"],
        )
        return self.success_response(
            data=payload,
            message="Upload URL created successfully.",
            status_code=status.HTTP_200_OK,
        )
