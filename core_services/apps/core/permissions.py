from rest_framework.permissions import BasePermission

from apps.authentication.rbac import (
    ensure_system_roles_for_user,
    user_has_all_permissions,
    user_has_any_permission,
    user_has_permission,
)


class HasPermissionCode(BasePermission):
    message = "You do not have permission to access this endpoint."

    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False

        ensure_system_roles_for_user(user)

        company_id = getattr(request, "company_id", None) or getattr(user, "company_id", None)

        permission_map = getattr(view, "required_permission_map", None) or {}
        required_permission = permission_map.get(request.method) or getattr(view, "required_permission", None)
        required_any_permissions = getattr(view, "required_any_permissions", None)
        required_all_permissions = getattr(view, "required_all_permissions", None)

        if required_permission and not user_has_permission(user, required_permission, company_id=company_id):
            return False
        if required_any_permissions and not user_has_any_permission(user, required_any_permissions, company_id=company_id):
            return False
        if required_all_permissions and not user_has_all_permissions(user, required_all_permissions, company_id=company_id):
            return False
        return True
