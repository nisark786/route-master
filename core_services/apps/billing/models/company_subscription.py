from django.db import models


class CompanySubscription(models.Model):
    company = models.OneToOneField("company.Company", on_delete=models.CASCADE)
    plan = models.ForeignKey("billing.SubscriptionPlan", on_delete=models.PROTECT)
    pending_plan = models.ForeignKey(
        "billing.SubscriptionPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pending_company_subscriptions",
    )
    pending_plan_effective_at = models.DateTimeField(null=True, blank=True)

    razorpay_payment_id = models.CharField(max_length=255, blank=True, default="")
    razorpay_order_id = models.CharField(max_length=255, blank=True, default="")
    razorpay_signature = models.CharField(max_length=255, blank=True, default="")

    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField()
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="INR")
    is_active = models.BooleanField(default=True)
