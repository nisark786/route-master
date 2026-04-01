from django.contrib.auth.hashers import make_password
from rest_framework import serializers

from apps.authentication.models import User
from apps.billing.models import SubscriptionPlan
from apps.company.models import Company


class StartRegistrationSerializer(serializers.Serializer):
    company_name = serializers.CharField(max_length=255)
    official_email = serializers.EmailField()
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    admin_email = serializers.EmailField()
    admin_password = serializers.CharField(min_length=8, write_only=True)
    plan_code = serializers.CharField(max_length=30)

    def validate_plan_code(self, value):
        return value.strip()

    def validate(self, attrs):
        plan = SubscriptionPlan.objects.filter(code__iexact=attrs["plan_code"], is_active=True).first()
        if not plan:
            raise serializers.ValidationError({"plan_code": "Invalid plan selected."})
        if User.objects.filter(email=attrs["admin_email"]).exists():
            raise serializers.ValidationError({"admin_email": "User already exists."})
        if Company.objects.filter(official_email=attrs["official_email"]).exists():
            raise serializers.ValidationError({"official_email": "Company email already exists."})

        attrs["plan"] = plan
        attrs["plan_code"] = plan.code
        attrs["admin_password_hash"] = make_password(attrs["admin_password"])
        return attrs
