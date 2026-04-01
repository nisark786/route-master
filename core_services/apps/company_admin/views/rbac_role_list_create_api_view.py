from django.db import IntegrityError
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.authentication.models import Role
from apps.company_admin.serializers import RbacRoleSerializer

from .base import CompanyAdminAPIView


class RbacRoleListCreateAPIView(CompanyAdminAPIView):
    required_permission_map = {
        "GET": "company_admin.rbac.manage",
        "POST": "company_admin.rbac.manage",
    }

    @swagger_auto_schema(
        tags=["Company Admin RBAC"],
        operation_summary="List company roles",
        responses={200: "Roles loaded"},
    )
    def get(self, request):
        roles = Role.objects.filter(company_id__in=[None, request.user.company_id], is_active=True).order_by("name")
        serializer = RbacRoleSerializer(roles, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin RBAC"],
        operation_summary="Create company role",
        request_body=RbacRoleSerializer,
        responses={201: "Role created"},
    )
    def post(self, request):
        serializer = RbacRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            role = serializer.save(company_id=request.user.company_id, is_system=False)
        except IntegrityError:
            raise ValidationError({"code": ["A role with this code already exists for this company."]})
        return Response(RbacRoleSerializer(role).data, status=status.HTTP_201_CREATED)
