from rest_framework import serializers

from apps.authentication.models import Permission, Role


class RbacRoleSerializer(serializers.ModelSerializer):
    permission_codes = serializers.ListField(
        child=serializers.CharField(max_length=120),
        required=False,
        allow_empty=True,
        write_only=True,
    )
    permissions = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Role
        fields = [
            "id",
            "code",
            "name",
            "description",
            "is_active",
            "is_system",
            "permission_codes",
            "permissions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "is_system", "created_at", "updated_at", "permissions"]

    def validate_code(self, value):
        cleaned = value.strip().lower().replace(" ", "_")
        if len(cleaned) < 3:
            raise serializers.ValidationError("Role code must be at least 3 characters.")
        return cleaned

    def _get_permissions_from_codes(self, codes):
        if not codes:
            return []
        permissions = list(Permission.objects.filter(code__in=codes, is_active=True))
        if len(permissions) != len(set(codes)):
            valid_codes = {item.code for item in permissions}
            missing = sorted(set(codes) - valid_codes)
            raise serializers.ValidationError({"permission_codes": [f"Invalid permission codes: {', '.join(missing)}"]})
        return permissions

    def get_permissions(self, obj):
        return [
            {"code": item.permission.code, "name": item.permission.name}
            for item in obj.role_permissions.select_related("permission").all().order_by("permission__code")
        ]

    def create(self, validated_data):
        permission_codes = validated_data.pop("permission_codes", [])
        role = Role.objects.create(**validated_data)
        permissions = self._get_permissions_from_codes(permission_codes)
        if permissions:
            role.permissions.set(permissions)
        return role

    def update(self, instance, validated_data):
        permission_codes = validated_data.pop("permission_codes", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()

        if permission_codes is not None:
            permissions = self._get_permissions_from_codes(permission_codes)
            instance.permissions.set(permissions)
        return instance
