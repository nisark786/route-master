from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("company_admin", "0005_expand_media_image_field_length"),
    ]

    operations = [
        migrations.AlterField(
            model_name="driverassignment",
            name="status",
            field=models.CharField(
                choices=[
                    ("ASSIGNED", "Assigned"),
                    ("IN_ROUTE", "In Route"),
                    ("COMPLETED", "Completed"),
                    ("CANCELLED", "Cancelled"),
                ],
                db_index=True,
                default="ASSIGNED",
                max_length=20,
            ),
        ),
    ]
