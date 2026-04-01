from rest_framework import serializers

from apps.authentication.models import User
from apps.authentication.rbac import get_user_permission_codes


class MeSerializer(serializers.ModelSerializer):
    permissions = serializers.SerializerMethodField()
    company_name = serializers.CharField(source="company.name", read_only=True)
    driver_name = serializers.CharField(source="driver_profile.name", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "mobile_number",
            "role",
            "company_id",
            "company_name",
            "driver_name",
            "must_change_password",
            "permissions",
        ]

    def get_permissions(self, obj):
        return sorted(get_user_permission_codes(obj, company_id=obj.company_id))
