from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.response import Response

from apps.authentication.models import User, UserRole
from apps.company_admin.serializers import RbacUserRoleAssignSerializer, RbacUserRoleSerializer

from .base import CompanyAdminAPIView


class RbacUserRoleListAssignAPIView(CompanyAdminAPIView):
    required_permission_map = {
        "GET": "company_admin.rbac.manage",
        "POST": "company_admin.rbac.manage",
    }

    @swagger_auto_schema(tags=["Company Admin RBAC"], operation_summary="List user role assignments")
    def get(self, request):
        assignments = (
            UserRole.objects.filter(user__company_id=request.user.company_id)
            .select_related("user", "role")
            .order_by("-created_at")
        )
        serializer = RbacUserRoleSerializer(assignments, many=True)
        users = list(
            User.objects.filter(company_id=request.user.company_id, is_active=True)
            .values("id", "email", "mobile_number", "role")
            .order_by("email", "mobile_number")
        )
        return Response({"assignments": serializer.data, "users": users}, status=status.HTTP_200_OK)

    @swagger_auto_schema(
        tags=["Company Admin RBAC"],
        operation_summary="Assign role to user",
        request_body=RbacUserRoleAssignSerializer,
    )
    def post(self, request):
        serializer = RbacUserRoleAssignSerializer(data=request.data, context={"company_id": request.user.company_id})
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        assignment, _ = UserRole.objects.update_or_create(
            user=payload["user"],
            role=payload["role"],
            company_id=request.user.company_id,
            defaults={"is_active": payload["is_active"]},
        )
        return Response(RbacUserRoleSerializer(assignment).data, status=status.HTTP_200_OK)
