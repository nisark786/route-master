from rest_framework import serializers

from apps.billing.models import SubscriptionPlan


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = ["id", "code", "name", "price", "duration_days", "features"]
