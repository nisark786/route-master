from django.db import IntegrityError
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.authentication.models import Role
from apps.company_admin.serializers import RbacRoleSerializer

from .base import CompanyAdminAPIView


class RbacRoleDetailAPIView(CompanyAdminAPIView):
    required_permission_map = {
        "GET": "company_admin.rbac.manage",
        "PATCH": "company_admin.rbac.manage",
        "DELETE": "company_admin.rbac.manage",
    }

    def _get_role(self, company_id, role_id):
        role = Role.objects.filter(id=role_id, company_id__in=[None, company_id]).first()
        if not role:
            raise NotFound("Role not found.")
        return role

    @swagger_auto_schema(tags=["Company Admin RBAC"], operation_summary="Get role details")
    def get(self, request, role_id):
        role = self._get_role(request.user.company_id, role_id)
        return Response(RbacRoleSerializer(role).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(tags=["Company Admin RBAC"], operation_summary="Update role", request_body=RbacRoleSerializer)
    def patch(self, request, role_id):
        role = self._get_role(request.user.company_id, role_id)
        if role.is_system and role.company_id is None:
            raise ValidationError({"role": ["System roles cannot be modified."]})

        serializer = RbacRoleSerializer(role, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            role = serializer.save()
        except IntegrityError:
            raise ValidationError({"code": ["A role with this code already exists for this company."]})
        return Response(RbacRoleSerializer(role).data, status=status.HTTP_200_OK)

    @swagger_auto_schema(tags=["Company Admin RBAC"], operation_summary="Delete role")
    def delete(self, request, role_id):
        role = self._get_role(request.user.company_id, role_id)
        if role.is_system and role.company_id is None:
            raise ValidationError({"role": ["System roles cannot be deleted."]})
        role.delete()
        return Response({"message": "Role deleted successfully."}, status=status.HTTP_200_OK)
