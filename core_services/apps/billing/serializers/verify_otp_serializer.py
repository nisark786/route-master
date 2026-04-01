from rest_framework import serializers

from apps.billing.models import PendingCompanyRegistration
from apps.billing.services import get_registration_otp_hash, verify_hashed_otp


class VerifyOtpSerializer(serializers.Serializer):
    registration_id = serializers.UUIDField()
    otp = serializers.CharField(max_length=6)

    def validate(self, attrs):
        registration = PendingCompanyRegistration.objects.filter(id=attrs["registration_id"]).first()
        if not registration:
            raise serializers.ValidationError({"registration_id": "Registration not found."})
        if registration.status == PendingCompanyRegistration.STATUS_COMPLETED:
            raise serializers.ValidationError({"registration_id": "Registration already completed."})

        hashed_otp = get_registration_otp_hash(registration.id)
        if not hashed_otp:
            registration.status = PendingCompanyRegistration.STATUS_EXPIRED
            registration.save(update_fields=["status", "updated_at"])
            raise serializers.ValidationError({"otp": "OTP expired. Please request a new OTP."})
        is_valid_otp = verify_hashed_otp(attrs["otp"], hashed_otp)
        if not is_valid_otp:
            raise serializers.ValidationError({"otp": "Invalid OTP."})

        attrs["registration"] = registration
        return attrs
