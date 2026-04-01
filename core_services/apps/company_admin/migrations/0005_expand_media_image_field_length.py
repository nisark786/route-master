from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("company_admin", "0004_product"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="image",
            field=models.ImageField(blank=True, max_length=255, null=True, upload_to="products/"),
        ),
        migrations.AlterField(
            model_name="shop",
            name="image",
            field=models.ImageField(blank=True, max_length=255, null=True, upload_to="shops/"),
        ),
    ]
