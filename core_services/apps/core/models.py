from django.db import models

class TenantModel(models.Model):
    company = models.ForeignKey(
        'company.Company', 
        on_delete=models.CASCADE,
        db_index=True
    )

    class Meta:
        abstract = True