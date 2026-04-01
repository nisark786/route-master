import uuid

from django.db import models


class Driver(models.Model):
    STATUS_AVAILABLE = "AVAILABLE"
    STATUS_IN_ROUTE = "IN_ROUTE"
    STATUS_ON_LEAVE = "ON_LEAVE"
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, "Available"),
        (STATUS_IN_ROUTE, "In Route"),
        (STATUS_ON_LEAVE, "On Leave"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField("authentication.User", on_delete=models.CASCADE, related_name="driver_profile")
    name = models.CharField(max_length=120)
    age = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "name"]),
        ]

    def __str__(self):
        return self.name
