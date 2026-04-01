# Generated manually for auth identity enhancements.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("authentication", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="mobile_number",
            field=models.CharField(blank=True, db_index=True, max_length=20, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="user",
            name="must_change_password",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
