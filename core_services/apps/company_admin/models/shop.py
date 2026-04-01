import uuid

from django.contrib.gis.db import models as gis_models
from django.db import models


class Shop(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("company.Company", on_delete=models.CASCADE, related_name="shops")
    name = models.CharField(max_length=120, db_index=True)
    owner_name = models.CharField(max_length=120, db_index=True)
    owner_mobile_number = models.CharField(max_length=20, blank=True, default="", db_index=True)
    owner_user = models.OneToOneField(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shop_profile",
    )
    location = models.CharField(max_length=255, blank=True, default="")
    location_display_name = models.CharField(max_length=255, blank=True, default="")
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    point = gis_models.PointField(srid=4326, geography=True, null=True, blank=True)
    image = models.ImageField(upload_to="shops/", max_length=255, null=True, blank=True)
    address = models.TextField(blank=True, default="")
    landmark = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "name", "owner_name"], name="uq_shop_company_name_owner"),
        ]
        indexes = [
            models.Index(fields=["company", "name"]),
            models.Index(fields=["company", "owner_name"]),
            models.Index(fields=["company", "owner_mobile_number"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.owner_name}"
