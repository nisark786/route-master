from django.db import models


class PlanChangeLog(models.Model):
    company = models.ForeignKey("company.Company", on_delete=models.CASCADE, related_name="plan_change_logs")
    old_plan = models.ForeignKey(
        "billing.SubscriptionPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="old_plan_logs",
    )
    new_plan = models.ForeignKey(
        "billing.SubscriptionPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="new_plan_logs",
    )
    changed_by = models.ForeignKey("authentication.User", on_delete=models.SET_NULL, null=True, blank=True)
    reason = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
