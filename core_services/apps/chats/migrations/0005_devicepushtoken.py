import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("chats", "0004_message_voice_fields"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DevicePushToken",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("token", models.CharField(db_index=True, max_length=512, unique=True)),
                (
                    "platform",
                    models.CharField(
                        choices=[("ANDROID", "Android"), ("IOS", "iOS"), ("WEB", "Web")],
                        default="ANDROID",
                        max_length=20,
                    ),
                ),
                ("is_active", models.BooleanField(db_index=True, default=True)),
                ("last_seen_at", models.DateTimeField(auto_now=True, db_index=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="device_push_tokens",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "indexes": [
                    models.Index(fields=["user", "is_active"], name="chats_devic_user_id_656852_idx"),
                    models.Index(fields=["platform", "is_active"], name="chats_devic_platfor_0e2f34_idx"),
                ],
            },
        ),
    ]
