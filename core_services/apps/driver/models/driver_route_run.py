import uuid

from django.db import models


class DriverRouteRun(models.Model):
    STATUS_IN_PROGRESS = "IN_PROGRESS"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CANCELLED = "CANCELLED"
    STATUS_CHOICES = [
        (STATUS_IN_PROGRESS, "In Progress"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.OneToOneField(
        "company_admin.DriverAssignment",
        on_delete=models.CASCADE,
        related_name="route_run",
    )
    driver = models.ForeignKey("company_admin.Driver", on_delete=models.CASCADE, related_name="route_runs")
    route = models.ForeignKey("company_admin.Route", on_delete=models.CASCADE, related_name="route_runs")
    vehicle = models.ForeignKey("company_admin.Vehicle", on_delete=models.CASCADE, related_name="route_runs")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_IN_PROGRESS, db_index=True)
    started_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-started_at", "-created_at"]
        indexes = [
            models.Index(fields=["driver", "status"]),
            models.Index(fields=["route", "status"]),
        ]

    def __str__(self):
        return f"{self.assignment_id}:{self.status}"
