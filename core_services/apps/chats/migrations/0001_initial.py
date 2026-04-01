import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("company", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Conversation",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("conversation_type", models.CharField(choices=[("DRIVER", "Driver"), ("ADMINISTRATION", "Administration")], db_index=True, max_length=30)),
                ("title", models.CharField(blank=True, default="", max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("last_message_at", models.DateTimeField(blank=True, db_index=True, null=True)),
                ("company", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="chat_conversations", to="company.company")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_chat_conversations", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-last_message_at", "-updated_at", "-created_at"]},
        ),
        migrations.CreateModel(
            name="Message",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("message_type", models.CharField(choices=[("TEXT", "Text"), ("SYSTEM", "System")], default="TEXT", max_length=20)),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="messages", to="chats.conversation")),
                ("sender", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="sent_chat_messages", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["created_at"]},
        ),
        migrations.CreateModel(
            name="ConversationParticipant",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("participant_role", models.CharField(choices=[("COMPANY_ADMIN", "Company Admin"), ("DRIVER", "Driver"), ("PLATFORM_ADMIN", "Platform Admin")], db_index=True, max_length=30)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("last_read_at", models.DateTimeField(blank=True, null=True)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="participants", to="chats.conversation")),
                ("last_read_message", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="+", to="chats.message")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chat_participations", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(fields=["company", "conversation_type"], name="chats_conve_company_6a958c_idx"),
        ),
        migrations.AddIndex(
            model_name="conversation",
            index=models.Index(fields=["conversation_type", "last_message_at"], name="chats_conve_convers_dca55c_idx"),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["conversation", "created_at"], name="chats_messa_convers_7371af_idx"),
        ),
        migrations.AddIndex(
            model_name="conversationparticipant",
            index=models.Index(fields=["user", "participant_role"], name="chats_conve_user_id_512359_idx"),
        ),
        migrations.AddIndex(
            model_name="conversationparticipant",
            index=models.Index(fields=["conversation", "participant_role"], name="chats_conve_convers_7853df_idx"),
        ),
        migrations.AddConstraint(
            model_name="conversationparticipant",
            constraint=models.UniqueConstraint(fields=("conversation", "user"), name="uq_chat_conversation_user"),
        ),
    ]
