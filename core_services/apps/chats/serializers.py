from rest_framework import serializers

from apps.authentication.models import User
from apps.chats.models import Conversation, ConversationParticipant, DevicePushToken, Message


class MessageSerializer(serializers.ModelSerializer):
    sender_id = serializers.UUIDField(source="sender.id", read_only=True)
    sender_email = serializers.EmailField(source="sender.email", read_only=True)
    sender_role = serializers.CharField(source="sender.role", read_only=True)
    is_edited = serializers.SerializerMethodField()
    recipient_count = serializers.SerializerMethodField()
    delivered_count = serializers.SerializerMethodField()
    seen_count = serializers.SerializerMethodField()
    audio_url = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id",
            "message_type",
            "content",
            "created_at",
            "updated_at",
            "sender_id",
            "sender_email",
            "sender_role",
            "is_edited",
            "recipient_count",
            "delivered_count",
            "seen_count",
            "audio_url",
            "duration_ms",
        ]

    def get_is_edited(self, obj):
        if not obj.updated_at or not obj.created_at:
            return False
        return obj.updated_at > obj.created_at

    def get_recipient_count(self, obj):
        annotated = getattr(obj, "_recipient_count", None)
        if annotated is not None:
            return int(annotated)
        sender_id = getattr(obj, "sender_id", None)
        return obj.conversation.participants.exclude(user_id=sender_id).count()

    def get_delivered_count(self, obj):
        annotated = getattr(obj, "_delivered_count", None)
        if annotated is not None:
            return int(annotated)
        return obj.receipts.exclude(delivered_at__isnull=True).count()

    def get_seen_count(self, obj):
        annotated = getattr(obj, "_seen_count", None)
        if annotated is not None:
            return int(annotated)
        return obj.receipts.exclude(seen_at__isnull=True).count()

    def get_audio_url(self, obj):
        if not obj.audio_file:
            return None
        request = self.context.get("request")
        url = obj.audio_file.url
        return request.build_absolute_uri(url) if request else url


class ConversationParticipantSerializer(serializers.ModelSerializer):
    user_id = serializers.UUIDField(source="user.id", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    mobile_number = serializers.CharField(source="user.mobile_number", read_only=True)
    user_role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = ConversationParticipant
        fields = [
            "id",
            "participant_role",
            "joined_at",
            "last_read_at",
            "user_id",
            "email",
            "mobile_number",
            "user_role",
        ]


class ConversationSerializer(serializers.ModelSerializer):
    participants = ConversationParticipantSerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = [
            "id",
            "conversation_type",
            "title",
            "company_id",
            "created_at",
            "updated_at",
            "last_message_at",
            "participants",
            "last_message",
            "unread_count",
        ]

    def get_last_message(self, obj):
        last_message = getattr(obj, "_prefetched_last_message", None)
        if last_message is None:
            last_message = obj.messages.order_by("-created_at").first()
        return MessageSerializer(last_message).data if last_message else None

    def get_unread_count(self, obj):
        annotated_unread_count = getattr(obj, "_annotated_unread_count", None)
        if annotated_unread_count is not None:
            return int(annotated_unread_count)

        request = self.context.get("request")
        if not request or not getattr(request, "user", None):
            return 0
        participant = next((item for item in obj.participants.all() if item.user_id == request.user.id), None)
        if not participant:
            return 0
        if not participant.last_read_message_id:
            return obj.messages.count()
        return obj.messages.filter(created_at__gt=participant.last_read_message.created_at).exclude(sender_id=request.user.id).count()


class ConversationListSerializer(serializers.ModelSerializer):
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()
    counterpart_user_id = serializers.UUIDField(read_only=True)

    class Meta:
        model = Conversation
        fields = [
            "id",
            "conversation_type",
            "company_id",
            "created_at",
            "updated_at",
            "last_message_at",
            "counterpart_user_id",
            "last_message",
            "unread_count",
        ]

    def get_last_message(self, obj):
        last_message = getattr(obj, "_prefetched_last_message", None)
        if last_message is None:
            return None
        return MessageSerializer(last_message).data

    def get_unread_count(self, obj):
        annotated_unread_count = getattr(obj, "_annotated_unread_count", None)
        if annotated_unread_count is not None:
            return int(annotated_unread_count)
        return 0


class MessageCreateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=4000)


class MessageUpdateSerializer(serializers.Serializer):
    content = serializers.CharField(max_length=4000)


class VoiceMessageCreateSerializer(serializers.Serializer):
    audio = serializers.FileField()
    duration_ms = serializers.IntegerField(required=False, min_value=1, max_value=10 * 60 * 1000)

    def validate_audio(self, value):
        max_size_bytes = 10 * 1024 * 1024
        if getattr(value, "size", 0) > max_size_bytes:
            raise serializers.ValidationError("Voice file is too large. Maximum size is 10MB.")
        content_type = str(getattr(value, "content_type", "") or "").lower()
        if content_type and not content_type.startswith("audio/"):
            raise serializers.ValidationError("Only audio files are allowed.")
        return value


class ConversationStartSerializer(serializers.Serializer):
    conversation_type = serializers.ChoiceField(choices=Conversation.TYPE_CHOICES)
    target_user_id = serializers.UUIDField()

    def validate_target_user_id(self, value):
        try:
            return User.objects.get(id=value, is_active=True)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("Target user not found.") from exc


class PushTokenRegisterSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)
    platform = serializers.ChoiceField(choices=DevicePushToken.PLATFORM_CHOICES, required=False)

    def validate_token(self, value):
        token = str(value or "").strip()
        if len(token) < 20:
            raise serializers.ValidationError("Invalid push token.")
        return token


class PushTokenUnregisterSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=512)

    def validate_token(self, value):
        token = str(value or "").strip()
        if not token:
            raise serializers.ValidationError("Push token is required.")
        return token
