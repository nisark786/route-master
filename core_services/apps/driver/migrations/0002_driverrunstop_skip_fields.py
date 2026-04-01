from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("driver", "0001_driver_route_run_and_driver_run_stop"),
    ]

    operations = [
        migrations.AddField(
            model_name="driverrunstop",
            name="skipped_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="driverrunstop",
            name="skip_reason",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="driverrunstop",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDING", "Pending"),
                    ("CHECKED_IN", "Checked In"),
                    ("COMPLETED", "Completed"),
                    ("SKIPPED", "Skipped"),
                ],
                db_index=True,
                default="PENDING",
                max_length=20,
            ),
        ),
    ]
