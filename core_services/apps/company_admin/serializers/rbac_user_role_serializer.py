from rest_framework import serializers

from apps.authentication.models import Role, User, UserRole


class RbacUserRoleSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)
    user_mobile_number = serializers.CharField(source="user.mobile_number", read_only=True)
    role_id = serializers.UUIDField(source="role.id", read_only=True)
    role_code = serializers.CharField(source="role.code", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)

    class Meta:
        model = UserRole
        fields = [
            "id",
            "user_id",
            "user_email",
            "user_mobile_number",
            "role_id",
            "role_code",
            "role_name",
            "is_active",
            "created_at",
            "updated_at",
        ]


class RbacUserRoleAssignSerializer(serializers.Serializer):
    user_id = serializers.UUIDField(required=True)
    role_id = serializers.UUIDField(required=True)
    is_active = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        company_id = self.context["company_id"]
        user = User.objects.filter(id=attrs["user_id"], company_id=company_id, is_active=True).first()
        if not user:
            raise serializers.ValidationError({"user_id": "User not found in this company."})
        role = Role.objects.filter(id=attrs["role_id"], is_active=True).first()
        if not role:
            raise serializers.ValidationError({"role_id": "Role not found."})
        if role.company_id not in [None, company_id]:
            raise serializers.ValidationError({"role_id": "Role does not belong to this company."})

        attrs["user"] = user
        attrs["role"] = role
        return attrs
