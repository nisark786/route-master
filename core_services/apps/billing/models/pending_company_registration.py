import uuid
from django.db import models


class PendingCompanyRegistration(models.Model):
    STATUS_PENDING_OTP = "PENDING_OTP"
    STATUS_PENDING_PAYMENT = "PENDING_PAYMENT"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_EXPIRED = "EXPIRED"

    STATUS_CHOICES = [
        (STATUS_PENDING_OTP, "Pending OTP"),
        (STATUS_PENDING_PAYMENT, "Pending Payment"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_EXPIRED, "Expired"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_name = models.CharField(max_length=255)
    official_email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=20, blank=True, default="")
    address = models.TextField(blank=True, default="")
    admin_email = models.EmailField(db_index=True)
    admin_password_hash = models.CharField(max_length=255)
    plan = models.ForeignKey(
        "billing.SubscriptionPlan",
        on_delete=models.PROTECT,
        related_name="pending_registrations",
    )

    otp_code = models.CharField(max_length=255, blank=True, default="")
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    is_verified = models.BooleanField(default=False)

    payment_order_id = models.CharField(max_length=255, blank=True, default="")
    payment_id = models.CharField(max_length=255, blank=True, default="")
    payment_signature = models.CharField(max_length=255, blank=True, default="")

    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING_OTP)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.company_name} - {self.status}"
