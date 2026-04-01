from django.db import migrations, models
import django.db.models.deletion
import django.core.validators
import uuid


class Migration(migrations.Migration):
    dependencies = [
        ("company", "0001_initial"),
        ("company_admin", "0003_driver_user_and_shop_owner_user"),
    ]

    operations = [
        migrations.CreateModel(
            name="Product",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(db_index=True, max_length=120)),
                ("image", models.ImageField(blank=True, null=True, upload_to="products/")),
                ("quantity_count", models.PositiveIntegerField(default=0, validators=[django.core.validators.MinValueValidator(0)])),
                ("rate", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(0)])),
                ("description", models.TextField(blank=True, default="")),
                ("shelf_life", models.CharField(blank=True, default="", max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="products", to="company.company"),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddConstraint(
            model_name="product",
            constraint=models.UniqueConstraint(fields=("company", "name"), name="uq_product_company_name"),
        ),
        migrations.AddIndex(
            model_name="product",
            index=models.Index(fields=["company", "name"], name="company_adm_company_265153_idx"),
        ),
    ]
