from rest_framework import serializers

from apps.billing.models import PendingCompanyRegistration


class RegistrationOnlySerializer(serializers.Serializer):
    registration_id = serializers.UUIDField()

    def validate_registration_id(self, value):
        registration = PendingCompanyRegistration.objects.filter(id=value).first()
        if not registration:
            raise serializers.ValidationError("Registration not found.")
        return value
