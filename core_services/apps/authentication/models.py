import uuid
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.core.cache import cache
from django.db import models
from .managers import UserManager


def _bump_user_authz_cache_version(user_id):
    key = f"authz:perm-version:{user_id}"
    current = cache.get(key, 1) or 1
    cache.set(key, int(current) + 1, timeout=60 * 60 * 24 * 30)


def _invalidate_user_profile_cache(user_id):
    cache.delete(f"user_profile:{user_id}")


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ("SUPER_ADMIN", "Super Admin"),
        ("COMPANY_ADMIN", "Company Admin"),
        ("DRIVER", "Driver"),
        ("SHOP_OWNER", "Shop Owner"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, db_index=True)
    mobile_number = models.CharField(max_length=20, unique=True, null=True, blank=True, db_index=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, db_index=True)
    company = models.ForeignKey("company.Company", on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_platform_admin = models.BooleanField(default=False)
    must_change_password = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        indexes = [
            models.Index(fields=["company", "role"]),
            models.Index(fields=["role", "is_active"]),
        ]

    def __str__(self):
        return self.email

    def _invalidate_cache(self):
        cache.delete(f"tenant_user:{self.id}")
        cache.delete(f"user_profile:{self.id}")
        _bump_user_authz_cache_version(self.id)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._invalidate_cache()

    def delete(self, *args, **kwargs):
        self._invalidate_cache()
        return super().delete(*args, **kwargs)


class Permission(models.Model):
    code = models.CharField(max_length=120, unique=True, db_index=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["code"]

    def __str__(self):
        return self.code


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("company.Company", on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    code = models.CharField(max_length=120, db_index=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True, default="")
    is_system = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    permissions = models.ManyToManyField("authentication.Permission", through="authentication.RolePermission", related_name="roles")

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["company", "code"], name="uq_role_company_code"),
            models.UniqueConstraint(
                fields=["code"],
                condition=models.Q(company__isnull=True),
                name="uq_role_global_code",
            ),
        ]
        indexes = [
            models.Index(fields=["company", "is_active"]),
            models.Index(fields=["company", "name"]),
        ]

    def __str__(self):
        return f"{self.code} ({self.company_id or 'GLOBAL'})"

    def save(self, *args, **kwargs):
        if self.pk:
            self.version = (self.version or 1) + 1
        result = super().save(*args, **kwargs)
        user_ids = list(self.role_users.values_list("user_id", flat=True).distinct())
        for user_id in user_ids:
            _bump_user_authz_cache_version(user_id)
            _invalidate_user_profile_cache(user_id)
        return result


class RolePermission(models.Model):
    role = models.ForeignKey("authentication.Role", on_delete=models.CASCADE, related_name="role_permissions")
    permission = models.ForeignKey("authentication.Permission", on_delete=models.CASCADE, related_name="permission_roles")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["role", "permission"], name="uq_role_permission"),
        ]
        indexes = [
            models.Index(fields=["role", "permission"]),
        ]

    def __str__(self):
        return f"{self.role_id}:{self.permission_id}"

    def _invalidate_related_users(self):
        user_ids = list(self.role.role_users.values_list("user_id", flat=True).distinct())
        for user_id in user_ids:
            _bump_user_authz_cache_version(user_id)
            _invalidate_user_profile_cache(user_id)

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        self._invalidate_related_users()
        return result

    def delete(self, *args, **kwargs):
        self._invalidate_related_users()
        return super().delete(*args, **kwargs)


class UserRole(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("authentication.User", on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey("authentication.Role", on_delete=models.CASCADE, related_name="role_users")
    company = models.ForeignKey("company.Company", on_delete=models.CASCADE, null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "role", "company"], name="uq_user_role_company"),
        ]
        indexes = [
            models.Index(fields=["user", "company", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.role_id}:{self.company_id or 'GLOBAL'}"

    def _invalidate_user_authz_cache(self):
        _bump_user_authz_cache_version(self.user_id)
        _invalidate_user_profile_cache(self.user_id)

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        self._invalidate_user_authz_cache()
        return result

    def delete(self, *args, **kwargs):
        self._invalidate_user_authz_cache()
        return super().delete(*args, **kwargs)
