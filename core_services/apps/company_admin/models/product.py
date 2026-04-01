import uuid

from django.core.validators import MinValueValidator
from django.db import models


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey("company.Company", on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=120, db_index=True)
    image = models.ImageField(upload_to="products/", max_length=255, null=True, blank=True)
    quantity_count = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0)])
    rate = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    description = models.TextField(blank=True, default="")
    shelf_life = models.CharField(max_length=80, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["company", "name"], name="uq_product_company_name"),
        ]
        indexes = [
            models.Index(fields=["company", "name"]),
        ]

    def __str__(self):
        return self.name
