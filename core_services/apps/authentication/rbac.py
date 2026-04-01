from django.core.cache import cache

from apps.authentication.models import Permission, Role, User, UserRole


DEFAULT_ROLE_PERMISSION_MAP = {
    "SUPER_ADMIN": {"main_admin.access"},
    "COMPANY_ADMIN": {
        "company_admin.access",
        "company_admin.rbac.manage",
        "vehicle.view",
        "vehicle.create",
        "vehicle.update",
        "vehicle.delete",
        "product.view",
        "product.create",
        "product.update",
        "product.delete",
        "shop.view",
        "shop.create",
        "shop.update",
        "shop.delete",
        "shop.reset_password",
        "driver.view",
        "driver.create",
        "driver.update",
        "driver.delete",
        "driver.reset_password",
        "driver_assignment.view",
        "driver_assignment.create",
        "driver_assignment.update",
        "driver_assignment.delete",
        "route.view",
        "route.create",
        "route.update",
        "route.delete",
        "ai.chat",
        "ai.dispatch",
        "ai.search",
        "ai.ingest",
        "ai.doc.update",
        "ai.doc.delete",
    },
    "DRIVER": {"driver.access"},
    "SHOP_OWNER": {"shop_owner.access"},
}


SYSTEM_PERMISSION_DEFINITIONS = [
    ("main_admin.access", "Main Admin Access", "Access main admin APIs."),
    ("company_admin.access", "Company Admin Access", "Access company admin APIs."),
    ("company_admin.rbac.manage", "RBAC Manage", "Manage company custom roles and assignments."),
    ("vehicle.view", "View Vehicles", "List and view vehicles."),
    ("vehicle.create", "Create Vehicles", "Create vehicles."),
    ("vehicle.update", "Update Vehicles", "Update vehicles."),
    ("vehicle.delete", "Delete Vehicles", "Delete vehicles."),
    ("product.view", "View Products", "List and view products."),
    ("product.create", "Create Products", "Create products."),
    ("product.update", "Update Products", "Update products."),
    ("product.delete", "Delete Products", "Delete products."),
    ("shop.view", "View Shops", "List and view shops."),
    ("shop.create", "Create Shops", "Create shops."),
    ("shop.update", "Update Shops", "Update shops."),
    ("shop.delete", "Delete Shops", "Delete shops."),
    ("shop.reset_password", "Reset Shop Owner Password", "Reset shop owner temporary passwords."),
    ("driver.view", "View Drivers", "List and view drivers."),
    ("driver.create", "Create Drivers", "Create drivers."),
    ("driver.update", "Update Drivers", "Update drivers."),
    ("driver.delete", "Delete Drivers", "Delete drivers."),
    ("driver.reset_password", "Reset Driver Password", "Reset driver temporary passwords."),
    ("driver_assignment.view", "View Driver Assignments", "List and view driver assignments."),
    ("driver_assignment.create", "Create Driver Assignments", "Create driver assignments."),
    ("driver_assignment.update", "Update Driver Assignments", "Update driver assignments."),
    ("driver_assignment.delete", "Delete Driver Assignments", "Delete driver assignments."),
    ("route.view", "View Routes", "List and view routes."),
    ("route.create", "Create Routes", "Create routes."),
    ("route.update", "Update Routes", "Update routes."),
    ("route.delete", "Delete Routes", "Delete routes."),
    ("ai.chat", "AI Assistant Chat", "Ask AI assistant with tenant context."),
    ("ai.dispatch", "AI Dispatch Copilot", "Get AI-powered dispatch recommendations."),
    ("ai.search", "AI Semantic Search", "Search tenant knowledge with embeddings."),
    ("ai.ingest", "AI Ingestion", "Ingest tenant knowledge into vector store."),
    ("ai.doc.update", "AI Document Update", "Update indexed AI knowledge documents."),
    ("ai.doc.delete", "AI Document Delete", "Delete indexed AI knowledge documents."),
    ("driver.access", "Driver Access", "Access driver app APIs."),
    ("shop_owner.access", "Shop Owner Access", "Access shop owner app APIs."),
]


SYSTEM_ROLE_DEFINITIONS = [
    ("super_admin", "Super Admin", None, {"main_admin.access"}),
    (
        "company_admin",
        "Company Admin",
        "COMPANY_ADMIN",
        {
            "company_admin.access",
            "company_admin.rbac.manage",
            "vehicle.view",
            "vehicle.create",
            "vehicle.update",
            "vehicle.delete",
            "product.view",
            "product.create",
            "product.update",
            "product.delete",
            "shop.view",
            "shop.create",
            "shop.update",
            "shop.delete",
            "shop.reset_password",
            "driver.view",
            "driver.create",
            "driver.update",
            "driver.delete",
            "driver.reset_password",
            "driver_assignment.view",
            "driver_assignment.create",
            "driver_assignment.update",
            "driver_assignment.delete",
            "route.view",
            "route.create",
            "route.update",
            "route.delete",
            "ai.chat",
            "ai.dispatch",
            "ai.search",
            "ai.ingest",
            "ai.doc.update",
            "ai.doc.delete",
        },
    ),
    ("driver", "Driver", "DRIVER", {"driver.access"}),
    ("shop_owner", "Shop Owner", "SHOP_OWNER", {"shop_owner.access"}),
]


def _cache_key_for_user_permissions(user_id, company_id):
    version = cache.get(f"authz:perm-version:{user_id}", 1) or 1
    company_part = company_id or "global"
    return f"authz:perm:{user_id}:{company_part}:v{version}"


def _cache_key_for_user_has_roles(user_id):
    version = cache.get(f"authz:perm-version:{user_id}", 1) or 1
    return f"authz:has-role:{user_id}:v{version}"


def get_user_permission_codes(user, company_id=None):
    if not user or not getattr(user, "is_authenticated", False):
        return set()

    target_company_id = company_id or getattr(user, "company_id", None)
    cache_key = _cache_key_for_user_permissions(user.id, target_company_id)
    cached = cache.get(cache_key)
    if cached is not None:
        return set(cached)

    assignments = (
        UserRole.objects.filter(user_id=user.id, is_active=True, role__is_active=True)
        .filter(role__company_id__in=[None, target_company_id])
        .filter(company_id__in=[None, target_company_id])
        .select_related("role")
        .prefetch_related("role__role_permissions__permission")
    )
    permission_codes = set()
    for assignment in assignments:
        for role_permission in assignment.role.role_permissions.all():
            if role_permission.permission.is_active:
                permission_codes.add(role_permission.permission.code)

    if not permission_codes:
        permission_codes = set(DEFAULT_ROLE_PERMISSION_MAP.get(getattr(user, "role", ""), set()))

    cache.set(cache_key, list(permission_codes), timeout=300)
    return permission_codes


def user_has_permission(user, permission_code, company_id=None):
    if not permission_code:
        return True
    return permission_code in get_user_permission_codes(user, company_id=company_id)


def user_has_any_permission(user, permission_codes, company_id=None):
    if not permission_codes:
        return True
    available = get_user_permission_codes(user, company_id=company_id)
    return any(code in available for code in permission_codes)


def user_has_all_permissions(user, permission_codes, company_id=None):
    if not permission_codes:
        return True
    available = get_user_permission_codes(user, company_id=company_id)
    return all(code in available for code in permission_codes)


def bump_user_permission_cache_version(user_id):
    key = f"authz:perm-version:{user_id}"
    current = cache.get(key, 1) or 1
    cache.set(key, int(current) + 1, timeout=60 * 60 * 24 * 30)


def ensure_system_roles_for_user(user):
    """
    Backward-compatible bridge:
    - if no explicit user role assignment exists yet, attach matching system role.
    """
    if not user:
        return
    has_roles_cache_key = _cache_key_for_user_has_roles(user.id)
    has_roles = cache.get(has_roles_cache_key)
    if has_roles is None:
        has_roles = UserRole.objects.filter(user_id=user.id, is_active=True).exists()
        cache.set(has_roles_cache_key, bool(has_roles), timeout=300)
    if has_roles:
        return

    code_to_role = {code: (role_code, permissions) for role_code, _name, code, permissions in SYSTEM_ROLE_DEFINITIONS if code}
    match = code_to_role.get(getattr(user, "role", ""))
    if not match:
        return
    role_code, _permissions = match
    role = Role.objects.filter(code=role_code, is_system=True).first()
    if not role:
        return
    UserRole.objects.get_or_create(
        user_id=user.id,
        role=role,
        company_id=user.company_id or None,
        defaults={"is_active": True},
    )
    cache.set(has_roles_cache_key, True, timeout=300)


def ensure_system_rbac_baseline():
    permission_map = {}
    for code, name, description in SYSTEM_PERMISSION_DEFINITIONS:
        permission, _ = Permission.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "description": description,
                "is_active": True,
            },
        )
        if not permission.name:
            permission.name = name
            permission.description = description
            permission.is_active = True
            permission.save(update_fields=["name", "description", "is_active", "updated_at"])
        permission_map[code] = permission

    for code, name, legacy_user_role, permission_codes in SYSTEM_ROLE_DEFINITIONS:
        role, _ = Role.objects.get_or_create(
            company=None,
            code=code,
            defaults={
                "name": name,
                "description": f"System role: {name}",
                "is_system": True,
                "is_active": True,
            },
        )
        if not role.is_system or not role.is_active:
            role.is_system = True
            role.is_active = True
            role.save(update_fields=["is_system", "is_active", "updated_at"])
        target_permissions = [permission_map[item] for item in permission_codes if item in permission_map]
        role.permissions.set(target_permissions)

        if legacy_user_role:
            users = User.objects.filter(role=legacy_user_role, is_active=True)
            for user in users:
                UserRole.objects.get_or_create(
                    user=user,
                    role=role,
                    company_id=user.company_id or None,
                    defaults={"is_active": True},
                )
