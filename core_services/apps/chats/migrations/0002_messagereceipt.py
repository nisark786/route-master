import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chats", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="MessageReceipt",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("delivered_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("seen_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("message", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="receipts", to="chats.message")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chat_message_receipts", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name="messagereceipt",
            index=models.Index(fields=["user", "delivered_at"], name="chats_messa_user_id_91f81a_idx"),
        ),
        migrations.AddIndex(
            model_name="messagereceipt",
            index=models.Index(fields=["user", "seen_at"], name="chats_messa_user_id_d31b1d_idx"),
        ),
        migrations.AddIndex(
            model_name="messagereceipt",
            index=models.Index(fields=["message", "user"], name="chats_messa_message_7dc9ce_idx"),
        ),
        migrations.AddConstraint(
            model_name="messagereceipt",
            constraint=models.UniqueConstraint(fields=("message", "user"), name="uq_chat_message_receipt_user"),
        ),
    ]
