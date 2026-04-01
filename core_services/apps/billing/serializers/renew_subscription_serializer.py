from rest_framework import serializers

from apps.billing.models import SubscriptionPlan


class RenewSubscriptionSerializer(serializers.Serializer):
    plan_code = serializers.CharField(max_length=30)
    razorpay_order_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    razorpay_payment_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    razorpay_signature = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_plan_code(self, value):
        plan = SubscriptionPlan.objects.filter(code__iexact=value.strip(), is_active=True).first()
        if not plan:
            raise serializers.ValidationError("Selected plan is not available.")
        self.context["plan"] = plan
        return plan.code
