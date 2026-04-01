import uuid

from django.db import models


class DriverAssignmentInventoryItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assignment = models.ForeignKey(
        "company_admin.DriverAssignment",
        on_delete=models.CASCADE,
        related_name="inventory_items",
    )
    driver = models.ForeignKey(
        "company_admin.Driver",
        on_delete=models.CASCADE,
        related_name="assignment_inventory_items",
    )
    product = models.ForeignKey(
        "company_admin.Product",
        on_delete=models.PROTECT,
        related_name="driver_assignment_inventory_items",
    )
    quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["assignment", "product"],
                name="uq_driver_assignment_inventory_assignment_product",
            )
        ]
        indexes = [
            models.Index(fields=["assignment", "product"]),
            models.Index(fields=["driver", "updated_at"]),
        ]

    def __str__(self):
        return f"{self.assignment_id}:{self.product_id}:{self.quantity}"
