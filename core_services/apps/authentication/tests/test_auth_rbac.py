import pytest

from apps.authentication.models import Permission, Role, RolePermission, UserRole
from apps.authentication.rbac import (
    ensure_system_rbac_baseline,
    ensure_system_roles_for_user,
    get_user_permission_codes,
    user_has_all_permissions,
    user_has_any_permission,
    user_has_permission,
)


@pytest.mark.django_db
def test_get_user_permission_codes_uses_default_role_map(company_admin_user):
    permission_codes = get_user_permission_codes(company_admin_user)

    assert "company_admin.access" in permission_codes
    assert "product.create" in permission_codes


@pytest.mark.django_db
def test_get_user_permission_codes_prefers_explicit_active_role_assignments(company_admin_user, company):
    permission = Permission.objects.create(code="custom.permission", name="Custom Permission")
    inactive_permission = Permission.objects.create(
        code="inactive.permission",
        name="Inactive Permission",
        is_active=False,
    )
    role = Role.objects.create(company=company, code="custom-role", name="Custom Role")
    RolePermission.objects.create(role=role, permission=permission)
    RolePermission.objects.create(role=role, permission=inactive_permission)
    UserRole.objects.create(user=company_admin_user, role=role, company=company)

    permission_codes = get_user_permission_codes(company_admin_user, company_id=company.id)

    assert "custom.permission" in permission_codes
    assert "inactive.permission" not in permission_codes
    assert "product.create" not in permission_codes


@pytest.mark.django_db
def test_permission_helpers_respect_explicit_assignments(company_admin_user, company):
    permission = Permission.objects.create(code="route.approve", name="Route Approve")
    role = Role.objects.create(company=company, code="route-role", name="Route Role")
    RolePermission.objects.create(role=role, permission=permission)
    UserRole.objects.create(user=company_admin_user, role=role, company=company)

    assert user_has_permission(company_admin_user, "route.approve", company_id=company.id) is True
    assert user_has_any_permission(
        company_admin_user,
        ["missing.permission", "route.approve"],
        company_id=company.id,
    ) is True
    assert user_has_all_permissions(
        company_admin_user,
        ["route.approve"],
        company_id=company.id,
    ) is True


@pytest.mark.django_db
def test_ensure_system_roles_for_user_attaches_matching_system_role(driver_user):
    ensure_system_rbac_baseline()

    ensure_system_roles_for_user(driver_user)

    assignment = UserRole.objects.filter(user=driver_user, is_active=True).select_related("role").first()
    assert assignment is not None
    assert assignment.role.code == "driver"
