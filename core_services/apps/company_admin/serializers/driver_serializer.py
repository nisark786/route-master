import re

from rest_framework import serializers

from apps.company_admin.models import Driver


MOBILE_PATTERN = re.compile(r"^\+?[0-9][0-9 -]{7,18}[0-9]$")


class DriverSerializer(serializers.ModelSerializer):
    mobile_number = serializers.CharField(source="user.mobile_number")
    user_id = serializers.UUIDField(source="user.id", read_only=True)

    class Meta:
        model = Driver
        fields = [
            "id",
            "user_id",
            "name",
            "mobile_number",
            "age",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_name(self, value):
        cleaned = value.strip()
        if len(cleaned) < 2:
            raise serializers.ValidationError("Driver name must be at least 2 characters.")
        return cleaned

    def validate_mobile_number(self, value):
        cleaned = re.sub(r"\s+", " ", value.strip())
        if not MOBILE_PATTERN.match(cleaned):
            raise serializers.ValidationError("Enter a valid mobile number.")
        return cleaned.replace(" ", "").replace("-", "")

    def validate_age(self, value):
        if value < 18 or value > 80:
            raise serializers.ValidationError("Driver age must be between 18 and 80.")
        return value

    def create(self, validated_data):
        user_value = validated_data.pop("user", None)
        if user_value is not None and not isinstance(user_value, dict):
            validated_data["user"] = user_value
        return super().create(validated_data)

    def update(self, instance, validated_data):
        user_value = validated_data.pop("user", None)
        if user_value is not None and not isinstance(user_value, dict):
            validated_data["user"] = user_value
        return super().update(instance, validated_data)
