import uuid

from django.db import models


class DriverAssignment(models.Model):
    STATUS_ASSIGNED = "ASSIGNED"
    STATUS_IN_ROUTE = "IN_ROUTE"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_CHOICES = [
        (STATUS_ASSIGNED, "Assigned"),
        (STATUS_IN_ROUTE, "In Route"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    driver = models.ForeignKey("company_admin.Driver", on_delete=models.CASCADE, related_name="assignments")
    route = models.ForeignKey("company_admin.Route", on_delete=models.CASCADE, related_name="driver_assignments")
    vehicle = models.ForeignKey("company_admin.Vehicle", on_delete=models.CASCADE, related_name="driver_assignments")
    scheduled_at = models.DateTimeField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ASSIGNED, db_index=True)
    notes = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["driver", "scheduled_at"], name="uq_driver_assignment_driver_datetime"),
            models.UniqueConstraint(fields=["vehicle", "scheduled_at"], name="uq_driver_assignment_vehicle_datetime"),
        ]
        indexes = [
            models.Index(fields=["driver", "scheduled_at"]),
            models.Index(fields=["route", "scheduled_at"]),
            models.Index(fields=["vehicle", "scheduled_at"]),
        ]

    def __str__(self):
        return f"{self.driver_id}:{self.route_id}:{self.scheduled_at}"
