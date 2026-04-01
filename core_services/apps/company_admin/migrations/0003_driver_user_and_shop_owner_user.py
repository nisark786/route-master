# Generated manually for driver/shop-owner identity consolidation.

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations, models
import django.db.models.deletion
import uuid


def _build_driver_email(company_id, mobile_number):
    digits = "".join(ch for ch in (mobile_number or "") if ch.isdigit()) or str(uuid.uuid4())[:8]
    return f"driver.{digits}.{str(company_id)[:8]}@local.routemaster"


def forward_backfill_driver_user(apps, schema_editor):
    Driver = apps.get_model("company_admin", "Driver")
    User = apps.get_model("authentication", "User")

    for driver in Driver.objects.all().iterator():
        if getattr(driver, "user_id", None):
            continue
        email = _build_driver_email(driver.company_id, driver.mobile_number)
        user = User.objects.create(
            email=email,
            mobile_number=driver.mobile_number,
            role="DRIVER",
            company_id=driver.company_id,
            is_active=True,
            must_change_password=True,
            password=make_password("Temp@1234"),
        )
        driver.user_id = user.id
        driver.save(update_fields=["user"])


def reverse_backfill_driver_user(apps, schema_editor):
    Driver = apps.get_model("company_admin", "Driver")
    User = apps.get_model("authentication", "User")
    for driver in Driver.objects.exclude(user_id=None).iterator():
        user = User.objects.filter(id=driver.user_id).first()
        if user:
            driver.mobile_number = user.mobile_number or ""
            driver.company_id = user.company_id
            driver.save(update_fields=["mobile_number", "company"])


class Migration(migrations.Migration):
    dependencies = [
        ("authentication", "0003_user_mobile_number_and_must_change_password"),
        ("company_admin", "0002_shop_point_and_display_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="shop",
            name="owner_mobile_number",
            field=models.CharField(blank=True, db_index=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="shop",
            name="owner_user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="shop_profile",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name="shop",
            index=models.Index(fields=["company", "owner_mobile_number"], name="company_adm_company_owner_mobile_idx"),
        ),
        migrations.AddField(
            model_name="driver",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="driver_profile",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.RunPython(forward_backfill_driver_user, reverse_backfill_driver_user),
        migrations.RemoveConstraint(
            model_name="driver",
            name="uq_driver_company_mobile_number",
        ),
        migrations.RemoveIndex(
            model_name="driver",
            name="company_adm_company_7a5405_idx",
        ),
        migrations.RemoveIndex(
            model_name="driver",
            name="company_adm_company_2b52b5_idx",
        ),
        migrations.RemoveField(
            model_name="driver",
            name="company",
        ),
        migrations.RemoveField(
            model_name="driver",
            name="mobile_number",
        ),
        migrations.AlterField(
            model_name="driver",
            name="user",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="driver_profile",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddIndex(
            model_name="driver",
            index=models.Index(fields=["user", "name"], name="company_adm_user_name_idx"),
        ),
    ]
