from rest_framework import serializers


class TemporaryPasswordResetSerializer(serializers.Serializer):
    temporary_password = serializers.CharField(required=True, allow_blank=False, min_length=8, max_length=128)
