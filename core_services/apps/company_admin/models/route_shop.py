import uuid

from django.db import models


class RouteShop(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route = models.ForeignKey("company_admin.Route", on_delete=models.CASCADE, related_name="route_shops")
    shop = models.ForeignKey("company_admin.Shop", on_delete=models.CASCADE, related_name="route_assignments")
    position = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["route", "position"], name="uq_route_shop_route_position"),
            models.UniqueConstraint(fields=["shop"], name="uq_route_shop_unique_shop"),
        ]
        indexes = [
            models.Index(fields=["route", "position"]),
            models.Index(fields=["shop"]),
        ]

    def __str__(self):
        return f"{self.route_id}:{self.shop_id}@{self.position}"
