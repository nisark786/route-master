from django.utils.translation import gettext_lazy as _
from django.db.models import Value
from django.db.models.functions import Replace
from rest_framework import serializers

from apps.authentication.models import User

class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False)
    mobile_number = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=True, write_only=True)

    def _normalize_mobile(self, value: str) -> str:
        return value.replace(" ", "").replace("-", "")

    def validate(self, attrs):
        identifier = (attrs.get("identifier") or attrs.get("email") or attrs.get("mobile_number") or "").strip()
        password = attrs.get("password")

        if not identifier or not password:
            raise serializers.ValidationError(_("Identifier and password are required."))

        # Driver/shop owner can login with mobile number; admins continue with email.
        if "@" in identifier:
            user = User.objects.filter(email__iexact=identifier).first()
        else:
            condensed_input = self._normalize_mobile(identifier)
            user = (
                User.objects.annotate(
                    normalized_mobile=Replace(
                        Replace("mobile_number", Value(" "), Value("")),
                        Value("-"),
                        Value(""),
                    )
                )
                .filter(normalized_mobile=condensed_input)
                .first()
            )

        if not user or not user.check_password(password):
            raise serializers.ValidationError(_("Invalid credentials."))
        if not user.is_active:
            raise serializers.ValidationError(_("Account is inactive."))

        attrs["user"] = user
        attrs["identifier"] = identifier
        return attrs
