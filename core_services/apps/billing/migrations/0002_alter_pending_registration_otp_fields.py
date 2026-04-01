from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="pendingcompanyregistration",
            name="otp_code",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="pendingcompanyregistration",
            name="otp_expires_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
