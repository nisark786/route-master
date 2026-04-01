from rest_framework import serializers


class ChangeInitialPasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user
        current_password = attrs["current_password"]
        new_password = attrs["new_password"]
        confirm_password = attrs["confirm_password"]

        if not user.check_password(current_password):
            raise serializers.ValidationError({"current_password": "Current password is incorrect."})
        if new_password != confirm_password:
            raise serializers.ValidationError({"confirm_password": "Password confirmation does not match."})
        if current_password == new_password:
            raise serializers.ValidationError({"new_password": "New password must be different from current password."})
        return attrs
