import uuid

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("company_admin", "0004_product"),
    ]

    operations = [
        migrations.CreateModel(
            name="DriverRouteRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "status",
                    models.CharField(
                        choices=[("IN_PROGRESS", "In Progress"), ("COMPLETED", "Completed"), ("CANCELLED", "Cancelled")],
                        db_index=True,
                        default="IN_PROGRESS",
                        max_length=20,
                    ),
                ),
                ("started_at", models.DateTimeField()),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "assignment",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="route_run",
                        to="company_admin.driverassignment",
                    ),
                ),
                (
                    "driver",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="route_runs",
                        to="company_admin.driver",
                    ),
                ),
                (
                    "route",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="route_runs",
                        to="company_admin.route",
                    ),
                ),
                (
                    "vehicle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="route_runs",
                        to="company_admin.vehicle",
                    ),
                ),
            ],
            options={"ordering": ["-started_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="DriverRunStop",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("position", models.PositiveIntegerField(db_index=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("PENDING", "Pending"), ("CHECKED_IN", "Checked In"), ("COMPLETED", "Completed")],
                        db_index=True,
                        default="PENDING",
                        max_length=20,
                    ),
                ),
                ("check_in_at", models.DateTimeField(blank=True, null=True)),
                ("check_out_at", models.DateTimeField(blank=True, null=True)),
                ("preordered_items", models.JSONField(blank=True, default=list)),
                ("ordered_items", models.JSONField(blank=True, default=list)),
                ("invoice_number", models.CharField(blank=True, default="", max_length=64)),
                ("invoice_total", models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ("invoice_file", models.FileField(blank=True, null=True, upload_to="invoices/")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "route_shop",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="run_stops",
                        to="company_admin.routeshop",
                    ),
                ),
                (
                    "run",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="stops",
                        to="driver.driverrouterun",
                    ),
                ),
                (
                    "shop",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="run_stops",
                        to="company_admin.shop",
                    ),
                ),
            ],
            options={"ordering": ["position", "created_at"]},
        ),
        migrations.AddIndex(
            model_name="driverrouterun",
            index=models.Index(fields=["driver", "status"], name="driver_driv_driver__f23d1f_idx"),
        ),
        migrations.AddIndex(
            model_name="driverrouterun",
            index=models.Index(fields=["route", "status"], name="driver_driv_route_i_0cd76c_idx"),
        ),
        migrations.AddIndex(
            model_name="driverrunstop",
            index=models.Index(fields=["run", "status"], name="driver_driv_run_id_047be9_idx"),
        ),
        migrations.AddIndex(
            model_name="driverrunstop",
            index=models.Index(fields=["shop", "status"], name="driver_driv_shop_id_14367f_idx"),
        ),
        migrations.AddConstraint(
            model_name="driverrunstop",
            constraint=models.UniqueConstraint(fields=("run", "position"), name="uq_driver_run_stop_run_position"),
        ),
        migrations.AddConstraint(
            model_name="driverrunstop",
            constraint=models.UniqueConstraint(fields=("run", "shop"), name="uq_driver_run_stop_run_shop"),
        ),
    ]
