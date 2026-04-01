from django.db import models


class PaymentTransaction(models.Model):
    STATUS_SUCCESS = "SUCCESS"
    STATUS_FAILED = "FAILED"
    STATUS_REFUNDED = "REFUNDED"
    STATUS_DISPUTED = "DISPUTED"
    STATUS_CHOICES = [
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUNDED, "Refunded"),
        (STATUS_DISPUTED, "Disputed"),
    ]

    company = models.ForeignKey("company.Company", on_delete=models.CASCADE, related_name="payment_transactions")
    subscription = models.ForeignKey("billing.CompanySubscription", on_delete=models.SET_NULL, null=True, blank=True)
    provider = models.CharField(max_length=50, default="razorpay")
    order_id = models.CharField(max_length=255, blank=True, default="")
    payment_id = models.CharField(max_length=255, blank=True, default="")
    invoice_number = models.CharField(max_length=64, blank=True, default="", db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=10, default="INR")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SUCCESS, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-paid_at"]
