from django.db import models
from django.core.cache import cache


class SubscriptionPlan(models.Model):
    code = models.CharField(max_length=30, unique=True, db_index=True)
    name = models.CharField(max_length=80)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    duration_days = models.IntegerField(default=30)
    features = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        cache.delete("billing:active_plans")
        return result

    def delete(self, *args, **kwargs):
        result = super().delete(*args, **kwargs)
        cache.delete("billing:active_plans")
        return result
