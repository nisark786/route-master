import uuid

from django.conf import settings
from django.db import models


class Conversation(models.Model):
    TYPE_DRIVER = "DRIVER"
    TYPE_ADMINISTRATION = "ADMINISTRATION"
    TYPE_CHOICES = [
      (TYPE_DRIVER, "Driver"),
      (TYPE_ADMINISTRATION, "Administration"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(
        "company.Company",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="chat_conversations",
        db_index=True,
    )
    conversation_type = models.CharField(max_length=30, choices=TYPE_CHOICES, db_index=True)
    title = models.CharField(max_length=255, blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_chat_conversations",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-last_message_at", "-updated_at", "-created_at"]
        indexes = [
            models.Index(fields=["company", "conversation_type"]),
            models.Index(fields=["conversation_type", "last_message_at"]),
        ]

    def __str__(self):
        return f"{self.conversation_type}:{self.id}"


class ConversationParticipant(models.Model):
    ROLE_COMPANY_ADMIN = "COMPANY_ADMIN"
    ROLE_DRIVER = "DRIVER"
    ROLE_PLATFORM_ADMIN = "PLATFORM_ADMIN"
    ROLE_CHOICES = [
        (ROLE_COMPANY_ADMIN, "Company Admin"),
        (ROLE_DRIVER, "Driver"),
        (ROLE_PLATFORM_ADMIN, "Platform Admin"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        "chats.Conversation",
        on_delete=models.CASCADE,
        related_name="participants",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_participations",
    )
    participant_role = models.CharField(max_length=30, choices=ROLE_CHOICES, db_index=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_message = models.ForeignKey(
        "chats.Message",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["conversation", "user"], name="uq_chat_conversation_user"),
        ]
        indexes = [
            models.Index(fields=["user", "participant_role"]),
            models.Index(fields=["conversation", "participant_role"]),
        ]

    def __str__(self):
        return f"{self.conversation_id}:{self.user_id}"


class Message(models.Model):
    TYPE_TEXT = "TEXT"
    TYPE_VOICE = "VOICE"
    TYPE_SYSTEM = "SYSTEM"
    TYPE_CHOICES = [
        (TYPE_TEXT, "Text"),
        (TYPE_VOICE, "Voice"),
        (TYPE_SYSTEM, "System"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    conversation = models.ForeignKey(
        "chats.Conversation",
        on_delete=models.CASCADE,
        related_name="messages",
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_chat_messages",
    )
    message_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_TEXT)
    content = models.TextField()
    audio_file = models.FileField(upload_to="chat/audio/%Y/%m/%d/", null=True, blank=True)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["conversation", "created_at"]),
        ]

    def __str__(self):
        return f"{self.conversation_id}:{self.id}"


class MessageReceipt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        "chats.Message",
        on_delete=models.CASCADE,
        related_name="receipts",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_message_receipts",
    )
    delivered_at = models.DateTimeField(null=True, blank=True, db_index=True)
    seen_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["message", "user"], name="uq_chat_message_receipt_user"),
        ]
        indexes = [
            models.Index(fields=["user", "delivered_at"]),
            models.Index(fields=["user", "seen_at"]),
            models.Index(fields=["message", "user"]),
        ]

    def __str__(self):
        return f"{self.message_id}:{self.user_id}"


class ChatUserPresence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="chat_presence",
    )
    is_online = models.BooleanField(default=False, db_index=True)
    last_seen_at = models.DateTimeField(null=True, blank=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_online", "last_seen_at"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{'online' if self.is_online else 'offline'}"


class DevicePushToken(models.Model):
    PLATFORM_ANDROID = "ANDROID"
    PLATFORM_IOS = "IOS"
    PLATFORM_WEB = "WEB"
    PLATFORM_CHOICES = [
        (PLATFORM_ANDROID, "Android"),
        (PLATFORM_IOS, "iOS"),
        (PLATFORM_WEB, "Web"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="device_push_tokens",
    )
    token = models.CharField(max_length=512, unique=True, db_index=True)
    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default=PLATFORM_ANDROID)
    is_active = models.BooleanField(default=True, db_index=True)
    last_seen_at = models.DateTimeField(auto_now=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["platform", "is_active"]),
        ]

    def __str__(self):
        return f"{self.user_id}:{self.platform}:{'active' if self.is_active else 'inactive'}"
