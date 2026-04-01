import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("company_admin", "0006_driverassignment_in_route_status"),
        ("driver", "0002_driverrunstop_skip_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="DriverAssignmentInventoryItem",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("quantity", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assignment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="inventory_items",
                        to="company_admin.driverassignment",
                    ),
                ),
                (
                    "driver",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assignment_inventory_items",
                        to="company_admin.driver",
                    ),
                ),
                (
                    "product",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="driver_assignment_inventory_items",
                        to="company_admin.product",
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at", "-created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="driverassignmentinventoryitem",
            constraint=models.UniqueConstraint(
                fields=("assignment", "product"),
                name="uq_driver_assignment_inventory_assignment_product",
            ),
        ),
        migrations.AddIndex(
            model_name="driverassignmentinventoryitem",
            index=models.Index(fields=["assignment", "product"], name="driver_assi_assignm_2e8a88_idx"),
        ),
        migrations.AddIndex(
            model_name="driverassignmentinventoryitem",
            index=models.Index(fields=["driver", "updated_at"], name="driver_assi_driver__fa95e8_idx"),
        ),
    ]
