import uuid

from django.db import models


def _empty_items():
    return []


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


class DriverRunStop(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_CHECKED_IN = "CHECKED_IN"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_CHECKED_IN, "Checked In"),
        (STATUS_COMPLETED, "Completed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    run = models.ForeignKey("driver.DriverRouteRun", on_delete=models.CASCADE, related_name="stops")
    route_shop = models.ForeignKey("company_admin.RouteShop", on_delete=models.PROTECT, related_name="run_stops")
    shop = models.ForeignKey("company_admin.Shop", on_delete=models.PROTECT, related_name="run_stops")
    position = models.PositiveIntegerField(db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    check_in_at = models.DateTimeField(null=True, blank=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    preordered_items = models.JSONField(default=_empty_items, blank=True)
    ordered_items = models.JSONField(default=_empty_items, blank=True)
    invoice_number = models.CharField(max_length=64, blank=True, default="")
    invoice_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    invoice_file = models.FileField(upload_to="invoices/", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position", "created_at"]
        constraints = [
            models.UniqueConstraint(fields=["run", "position"], name="uq_driver_run_stop_run_position"),
            models.UniqueConstraint(fields=["run", "shop"], name="uq_driver_run_stop_run_shop"),
        ]
        indexes = [
            models.Index(fields=["run", "status"]),
            models.Index(fields=["shop", "status"]),
        ]

    def __str__(self):
        return f"{self.run_id}:{self.shop_id}@{self.position}:{self.status}"
