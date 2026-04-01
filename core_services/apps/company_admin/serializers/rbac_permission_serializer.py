from rest_framework import serializers

from apps.authentication.models import Permission


class RbacPermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "code", "name", "description", "is_active"]
