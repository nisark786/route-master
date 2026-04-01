from django.conf import settings
from django.db import models


class CompanyActivityLog(models.Model):
    company = models.ForeignKey("company.Company", on_delete=models.CASCADE, related_name="activity_logs")
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=120)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_id} - {self.action}"
