from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0002_alter_pending_registration_otp_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="companysubscription",
            name="pending_plan",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="pending_company_subscriptions",
                to="billing.subscriptionplan",
            ),
        ),
        migrations.AddField(
            model_name="companysubscription",
            name="pending_plan_effective_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
