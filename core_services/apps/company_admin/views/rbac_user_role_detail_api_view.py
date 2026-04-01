from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.authentication.models import UserRole

from .base import CompanyAdminAPIView


class RbacUserRoleDetailAPIView(CompanyAdminAPIView):
    required_permission = "company_admin.rbac.manage"

    def _get_assignment(self, company_id, assignment_id):
        assignment = UserRole.objects.filter(id=assignment_id, user__company_id=company_id).first()
        if not assignment:
            raise NotFound("User role assignment not found.")
        return assignment

    @swagger_auto_schema(tags=["Company Admin RBAC"], operation_summary="Delete user role assignment")
    def delete(self, request, assignment_id):
        assignment = self._get_assignment(request.user.company_id, assignment_id)
        assignment.delete()
        return Response({"message": "Role assignment removed successfully."}, status=status.HTTP_200_OK)
