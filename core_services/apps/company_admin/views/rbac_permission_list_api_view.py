from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from apps.authentication.models import Permission
from apps.company_admin.serializers import RbacPermissionSerializer

from .base import CompanyAdminAPIView


class RbacPermissionListAPIView(CompanyAdminAPIView):
    required_permission = "company_admin.rbac.manage"

    @swagger_auto_schema(
        tags=["Company Admin RBAC"],
        operation_summary="List available permissions",
        responses={200: "Permissions loaded"},
    )
    def get(self, request):
        permissions = Permission.objects.filter(is_active=True).order_by("code")
        serializer = RbacPermissionSerializer(permissions, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
