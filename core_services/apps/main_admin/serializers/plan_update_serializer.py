from decimal import Decimal, ROUND_HALF_UP

from rest_framework import serializers

from apps.billing.models import SubscriptionPlan


class PlanUpdateSerializer(serializers.ModelSerializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=Decimal("0.00"), required=False)

    class Meta:
        model = SubscriptionPlan
        fields = ["name", "price", "duration_days", "features", "is_active"]

    def validate_price(self, value):
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
