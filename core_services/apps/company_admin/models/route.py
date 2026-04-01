import uuid

from django.db import models


class Route(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("company.Company", on_delete=models.CASCADE, related_name="routes")
    route_name = models.CharField(max_length=120)
    start_point = models.CharField(max_length=255)
    end_point = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "route_name"], name="uq_route_company_route_name"),
        ]
        indexes = [
            models.Index(fields=["company", "route_name"]),
        ]

    def __str__(self):
        return self.route_name
