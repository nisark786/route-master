import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Vehicle(models.Model):
    STATUS_AVAILABLE = "AVAILABLE"
    STATUS_ON_ROUTE = "ON_ROUTE"
    STATUS_RENOVATION = "RENOVATION"
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, "Available"),
        (STATUS_ON_ROUTE, "On Route"),
        (STATUS_RENOVATION, "Renovation"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("company.Company", on_delete=models.CASCADE, related_name="vehicles")
    name = models.CharField(max_length=100)
    number_plate = models.CharField(max_length=20, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE, db_index=True)
    fuel_percentage = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        default=100,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "number_plate"], name="uq_vehicle_company_number_plate"),
        ]

    def __str__(self):
        return f"{self.name} ({self.number_plate})"
