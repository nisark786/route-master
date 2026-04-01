from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from apps.company.models import Company


class CompanyProfileSerializer(serializers.ModelSerializer):
    subscription = serializers.SerializerMethodField()

    class Meta:
        model = Company
        fields = [
            "id",
            "name",
            "official_email",
            "phone",
            "address",
            "is_active",
            "is_email_verified",
            "subscription",
        ]

    def get_subscription(self, obj):
        try:
            subscription = obj.companysubscription
        except ObjectDoesNotExist:
            subscription = None
        if not subscription:
            return None
        plan = getattr(subscription, "plan", None)
        if not plan:
            return None
        return {
            "plan_code": plan.code,
            "plan_name": plan.name,
            "amount_paid": str(subscription.amount_paid),
            "start_date": subscription.start_date,
            "end_date": subscription.end_date,
            "is_active": subscription.is_active,
            "queued_plan_code": (
                subscription.pending_plan.code if getattr(subscription, "pending_plan", None) else None
            ),
            "queued_plan_name": (
                subscription.pending_plan.name if getattr(subscription, "pending_plan", None) else None
            ),
            "queued_plan_effective_at": subscription.pending_plan_effective_at,
        }
