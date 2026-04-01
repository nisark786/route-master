from django.core.cache import cache
from django.db import transaction
from django.db.models import Case, CharField, Count, DateTimeField, F, IntegerField, OuterRef, Q, Subquery, UUIDField, Value, When
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.authentication.models import User
from apps.chats.models import ChatUserPresence, Conversation, ConversationParticipant, DevicePushToken, Message, MessageReceipt


def _chat_list_cache_version(user_id):
    return f"chat:list:version:{user_id}"


def _chat_socket_connection_count_key(user_id):
    return f"chat:ws:connections:{user_id}"


def get_chat_list_cache_version(user_id):
    return cache.get(_chat_list_cache_version(user_id), 1)


def bump_chat_list_cache_version(user_ids):
    for user_id in {str(user_id) for user_id in user_ids if user_id}:
        key = _chat_list_cache_version(user_id)
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 2, timeout=None)


def bump_conversation_cache_for_participants(conversation):
    participant_ids = conversation.participants.values_list("user_id", flat=True)
    bump_chat_list_cache_version(participant_ids)


def get_presence_snapshot_for_users(user_ids):
    normalized_user_ids = [str(user_id) for user_id in user_ids if user_id]
    if not normalized_user_ids:
        return {}
    rows = ChatUserPresence.objects.filter(user_id__in=normalized_user_ids).values(
        "user_id",
        "is_online",
        "last_seen_at",
    )
    return {
        str(row["user_id"]): {
            "is_online": bool(row["is_online"]),
            "last_seen_at": row["last_seen_at"],
        }
        for row in rows
    }


def set_user_chat_online(user):
    presence, _ = ChatUserPresence.objects.get_or_create(user_id=user.id)
    if presence.is_online:
        return {
            "user_id": str(user.id),
            "is_online": True,
            "last_seen_at": presence.last_seen_at,
            "changed": False,
        }
    presence.is_online = True
    presence.save(update_fields=["is_online", "updated_at"])
    return {
        "user_id": str(user.id),
        "is_online": True,
        "last_seen_at": presence.last_seen_at,
        "changed": True,
    }


def set_user_chat_offline(user):
    now = timezone.now()
    presence, _ = ChatUserPresence.objects.get_or_create(user_id=user.id)
    if not presence.is_online and presence.last_seen_at:
        return {
            "user_id": str(user.id),
            "is_online": False,
            "last_seen_at": presence.last_seen_at,
            "changed": False,
        }
    presence.is_online = False
    presence.last_seen_at = now
    presence.save(update_fields=["is_online", "last_seen_at", "updated_at"])
    return {
        "user_id": str(user.id),
        "is_online": False,
        "last_seen_at": now,
        "changed": True,
    }


def get_conversation_ids_for_user(user):
    return list(
        ConversationParticipant.objects.filter(user_id=user.id).values_list("conversation_id", flat=True).distinct()
    )


def register_chat_socket_connection(user):
    key = _chat_socket_connection_count_key(user.id)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=None)
        count = 1
    if count == 1:
        return set_user_chat_online(user)
    presence = ChatUserPresence.objects.filter(user_id=user.id).values("last_seen_at").first() or {}
    return {
        "user_id": str(user.id),
        "is_online": True,
        "last_seen_at": presence.get("last_seen_at"),
        "changed": False,
    }


def unregister_chat_socket_connection(user):
    key = _chat_socket_connection_count_key(user.id)
    current_count = int(cache.get(key) or 0)
    if current_count > 1:
        cache.decr(key)
        presence = ChatUserPresence.objects.filter(user_id=user.id).values("last_seen_at").first() or {}
        return {
            "user_id": str(user.id),
            "is_online": True,
            "last_seen_at": presence.get("last_seen_at"),
            "changed": False,
        }
    if current_count == 1:
        cache.delete(key)
        return set_user_chat_offline(user)
    return set_user_chat_offline(user)


def _participant_role_for_user(user):
    if user.role == "COMPANY_ADMIN":
        return ConversationParticipant.ROLE_COMPANY_ADMIN
    if user.role == "DRIVER":
        return ConversationParticipant.ROLE_DRIVER
    if user.role == "SUPER_ADMIN":
        return ConversationParticipant.ROLE_PLATFORM_ADMIN
    raise ValidationError({"user": ["This user role is not supported for chat."]})


def _validate_conversation_target(request_user, conversation_type, target_user):
    if request_user.role == "COMPANY_ADMIN":
        if conversation_type == Conversation.TYPE_DRIVER:
            if target_user.role != "DRIVER" or target_user.company_id != request_user.company_id:
                raise PermissionDenied("Company admin can only chat with drivers in the same company.")
            return request_user.company
        if conversation_type == Conversation.TYPE_ADMINISTRATION:
            if target_user.role != "SUPER_ADMIN":
                raise PermissionDenied("Administration chat must target a platform admin.")
            return request_user.company

    if request_user.role == "DRIVER":
        if conversation_type != Conversation.TYPE_DRIVER:
            raise PermissionDenied("Drivers can only use driver conversations.")
        if target_user.role != "COMPANY_ADMIN" or target_user.company_id != request_user.company_id:
            raise PermissionDenied("Driver can only chat with company admins in the same company.")
        return request_user.company

    if request_user.role == "SUPER_ADMIN":
        if conversation_type != Conversation.TYPE_ADMINISTRATION:
            raise PermissionDenied("Platform admins can only use administration conversations here.")
        if target_user.role != "COMPANY_ADMIN":
            raise PermissionDenied("Administration chat must target a company admin.")
        return target_user.company

    raise PermissionDenied("This role cannot create chat conversations.")


def get_accessible_conversations_for_user(user, scope=None):
    latest_message_queryset = Message.objects.filter(conversation_id=OuterRef("pk")).order_by("-created_at")
    latest_message_id_subquery = (
        latest_message_queryset.values("id")[:1]
    )
    latest_message_content_subquery = (
        latest_message_queryset.values("content")[:1]
    )
    latest_message_created_at_subquery = (
        latest_message_queryset.values("created_at")[:1]
    )
    latest_message_updated_at_subquery = (
        latest_message_queryset.values("updated_at")[:1]
    )
    latest_message_sender_id_subquery = (
        latest_message_queryset.values("sender_id")[:1]
    )
    latest_message_sender_email_subquery = (
        latest_message_queryset.values("sender__email")[:1]
    )
    latest_message_sender_role_subquery = (
        latest_message_queryset.values("sender__role")[:1]
    )
    latest_message_type_subquery = (
        latest_message_queryset.values("message_type")[:1]
    )
    last_read_message_id_subquery = (
        ConversationParticipant.objects.filter(conversation_id=OuterRef("pk"), user_id=user.id)
        .values("last_read_message_id")[:1]
    )
    last_read_message_created_at_subquery = (
        ConversationParticipant.objects.filter(conversation_id=OuterRef("pk"), user_id=user.id)
        .values("last_read_message__created_at")[:1]
    )
    total_messages_subquery = (
        Message.objects.filter(conversation_id=OuterRef("pk"))
        .order_by()
        .values("conversation_id")
        .annotate(count=Count("id"))
        .values("count")[:1]
    )
    unread_messages_subquery = (
        Message.objects.filter(
            conversation_id=OuterRef("pk"),
            created_at__gt=Subquery(last_read_message_created_at_subquery),
        )
        .exclude(sender_id=user.id)
        .order_by()
        .values("conversation_id")
        .annotate(count=Count("id"))
        .values("count")[:1]
    )
    counterpart_user_id_subquery = (
        ConversationParticipant.objects.filter(conversation_id=OuterRef("pk"))
        .exclude(user_id=user.id)
        .values("user_id")[:1]
    )

    qs = (
        Conversation.objects.filter(participants__user_id=user.id)
        .distinct()
        .annotate(
            _last_message_id=Subquery(latest_message_id_subquery),
            _last_read_message_id=Subquery(last_read_message_id_subquery),
            counterpart_user_id=Subquery(counterpart_user_id_subquery),
            _last_message_content=Subquery(latest_message_content_subquery, output_field=CharField()),
            _last_message_created_at=Subquery(latest_message_created_at_subquery, output_field=DateTimeField()),
            _last_message_updated_at=Subquery(latest_message_updated_at_subquery, output_field=DateTimeField()),
            _last_message_sender_id=Subquery(latest_message_sender_id_subquery, output_field=UUIDField()),
            _last_message_sender_email=Subquery(latest_message_sender_email_subquery, output_field=CharField()),
            _last_message_sender_role=Subquery(latest_message_sender_role_subquery, output_field=CharField()),
            _last_message_type=Subquery(latest_message_type_subquery, output_field=CharField()),
        )
        .annotate(
            _annotated_unread_count=Case(
                When(
                    _last_read_message_id__isnull=True,
                    then=Coalesce(Subquery(total_messages_subquery, output_field=IntegerField()), Value(0)),
                ),
                default=Coalesce(Subquery(unread_messages_subquery, output_field=IntegerField()), Value(0)),
                output_field=IntegerField(),
            )
        )
    )

    if user.role in {"COMPANY_ADMIN", "DRIVER"}:
        qs = qs.filter(company_id=user.company_id)

    if user.role == "COMPANY_ADMIN" and scope == "drivers":
        qs = qs.filter(conversation_type=Conversation.TYPE_DRIVER)
    elif user.role == "COMPANY_ADMIN" and scope == "administration":
        qs = qs.filter(conversation_type=Conversation.TYPE_ADMINISTRATION)
    elif user.role == "SUPER_ADMIN" and scope == "administration":
        qs = qs.filter(conversation_type=Conversation.TYPE_ADMINISTRATION)
    elif user.role == "DRIVER":
        qs = qs.filter(conversation_type=Conversation.TYPE_DRIVER)

    return qs.order_by("-last_message_at", "-updated_at", "-created_at")


def get_accessible_contacts_for_user(user, scope=None):
    if user.role == "COMPANY_ADMIN":
        if scope == "administration":
            return User.objects.filter(role="SUPER_ADMIN", is_active=True).values(
                "id",
                "email",
                "mobile_number",
                "role",
                "company_id",
            ).order_by("email")
        return (
            User.objects.filter(role="DRIVER", company_id=user.company_id, is_active=True)
            .values(
                "id",
                "email",
                "mobile_number",
                "role",
                "company_id",
                "driver_profile__name",
            )
            .order_by("driver_profile__name", "email", "mobile_number")
        )
    if user.role == "SUPER_ADMIN":
        return User.objects.filter(role="COMPANY_ADMIN", is_active=True).values(
            "id",
            "email",
            "mobile_number",
            "role",
            "company_id",
            "company__name",
        ).order_by("email")
    if user.role == "DRIVER":
        return User.objects.filter(role="COMPANY_ADMIN", company_id=user.company_id, is_active=True).values(
            "id",
            "email",
            "mobile_number",
            "role",
            "company_id",
            "company__name",
        ).order_by("email")
    return User.objects.none()


@transaction.atomic
def get_or_create_conversation(*, request_user, target_user, conversation_type):
    company = _validate_conversation_target(request_user, conversation_type, target_user)

    target_ids = [request_user.id, target_user.id]
    conversation = (
        Conversation.objects.filter(conversation_type=conversation_type)
        .filter(company=company)
        .annotate(
            participant_count=Count("participants", distinct=True),
            matched_participant_count=Count(
                "participants",
                filter=Q(participants__user_id__in=target_ids),
                distinct=True,
            ),
        )
        .filter(participant_count=2, matched_participant_count=2)
        .distinct()
        .first()
    )

    if conversation:
        return conversation, False

    conversation = Conversation.objects.create(
        company=company,
        conversation_type=conversation_type,
        created_by=request_user,
        title="",
        last_message_at=timezone.now(),
    )
    ConversationParticipant.objects.bulk_create(
        [
            ConversationParticipant(
                conversation=conversation,
                user=request_user,
                participant_role=_participant_role_for_user(request_user),
            ),
            ConversationParticipant(
                conversation=conversation,
                user=target_user,
                participant_role=_participant_role_for_user(target_user),
            ),
        ]
    )
    bump_chat_list_cache_version(target_ids)
    return conversation, True


def ensure_user_in_conversation(user, conversation):
    participant = (
        ConversationParticipant.objects.select_related("last_read_message")
        .filter(conversation_id=conversation.id, user_id=user.id)
        .first()
    )
    if not participant:
        raise PermissionDenied("You are not a participant in this conversation.")
    return participant


def annotate_messages_with_receipt_counts(queryset):
    recipient_count_subquery = (
        ConversationParticipant.objects.filter(conversation_id=OuterRef("conversation_id"))
        .exclude(user_id=OuterRef("sender_id"))
        .order_by()
        .values("conversation_id")
        .annotate(count=Count("id"))
        .values("count")[:1]
    )
    delivered_count_subquery = (
        MessageReceipt.objects.filter(message_id=OuterRef("pk"), delivered_at__isnull=False)
        .order_by()
        .values("message_id")
        .annotate(count=Count("id"))
        .values("count")[:1]
    )
    seen_count_subquery = (
        MessageReceipt.objects.filter(message_id=OuterRef("pk"), seen_at__isnull=False)
        .order_by()
        .values("message_id")
        .annotate(count=Count("id"))
        .values("count")[:1]
    )

    return queryset.annotate(
        _recipient_count=Coalesce(Subquery(recipient_count_subquery, output_field=IntegerField()), Value(0)),
        _delivered_count=Coalesce(Subquery(delivered_count_subquery, output_field=IntegerField()), Value(0)),
        _seen_count=Coalesce(Subquery(seen_count_subquery, output_field=IntegerField()), Value(0)),
    )


def _touch_conversation_after_send(conversation, sender, message):
    conversation.last_message_at = message.created_at
    conversation.save(update_fields=["last_message_at", "updated_at"])
    ConversationParticipant.objects.filter(conversation_id=conversation.id, user_id=sender.id).update(
        last_read_message=message,
        last_read_at=message.created_at,
    )
    recipient_ids = list(
        ConversationParticipant.objects.filter(conversation_id=conversation.id)
        .exclude(user_id=sender.id)
        .values_list("user_id", flat=True)
    )
    MessageReceipt.objects.bulk_create(
        [MessageReceipt(message=message, user_id=user_id) for user_id in recipient_ids],
        ignore_conflicts=True,
    )
    bump_conversation_cache_for_participants(conversation)


def register_device_push_token(*, user, token, platform):
    normalized_token = str(token or "").strip()
    token_row, _ = DevicePushToken.objects.update_or_create(
        token=normalized_token,
        defaults={
            "user": user,
            "platform": platform or DevicePushToken.PLATFORM_ANDROID,
            "is_active": True,
        },
    )
    DevicePushToken.objects.filter(user_id=user.id, is_active=True).exclude(id=token_row.id).update(is_active=False)
    return token_row


def unregister_device_push_token(*, user, token):
    updated = DevicePushToken.objects.filter(user_id=user.id, token=token, is_active=True).update(is_active=False)
    return bool(updated)


def dispatch_chat_push_notification(message):
    from apps.chats.tasks import send_chat_message_push_task

    send_chat_message_push_task.delay(str(message.id))


@transaction.atomic
def create_message(*, conversation, sender, content):
    ensure_user_in_conversation(sender, conversation)
    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        message_type=Message.TYPE_TEXT,
        content=content.strip(),
    )
    _touch_conversation_after_send(conversation, sender, message)
    dispatch_chat_push_notification(message)
    return message


@transaction.atomic
def create_voice_message(*, conversation, sender, audio_file, duration_ms=None):
    ensure_user_in_conversation(sender, conversation)
    message = Message.objects.create(
        conversation=conversation,
        sender=sender,
        message_type=Message.TYPE_VOICE,
        content="",
        audio_file=audio_file,
        duration_ms=duration_ms,
    )
    _touch_conversation_after_send(conversation, sender, message)
    dispatch_chat_push_notification(message)
    return message


@transaction.atomic
def update_message(*, conversation, message, user, content):
    ensure_user_in_conversation(user, conversation)
    if message.conversation_id != conversation.id:
        raise PermissionDenied("Message does not belong to this conversation.")
    if message.sender_id != user.id:
        raise PermissionDenied("You can only edit your own messages.")
    if message.message_type != Message.TYPE_TEXT:
        raise ValidationError({"message": ["Only text messages can be edited."]})

    message.content = content.strip()
    message.save(update_fields=["content", "updated_at"])
    bump_conversation_cache_for_participants(conversation)
    return message


@transaction.atomic
def delete_message(*, conversation, message, user):
    ensure_user_in_conversation(user, conversation)
    if message.conversation_id != conversation.id:
        raise PermissionDenied("Message does not belong to this conversation.")
    if message.sender_id != user.id:
        raise PermissionDenied("You can only delete your own messages.")
    if message.message_type == Message.TYPE_SYSTEM:
        raise ValidationError({"message": ["System messages cannot be deleted."]})

    replacement_last_message = (
        Message.objects.filter(conversation_id=conversation.id)
        .exclude(id=message.id)
        .order_by("-created_at")
        .first()
    )

    ConversationParticipant.objects.filter(last_read_message_id=message.id).update(
        last_read_message=replacement_last_message,
        last_read_at=timezone.now() if replacement_last_message else None,
    )

    message_id = str(message.id)
    message.delete()

    conversation.last_message_at = replacement_last_message.created_at if replacement_last_message else None
    conversation.save(update_fields=["last_message_at", "updated_at"])
    bump_conversation_cache_for_participants(conversation)
    return {
        "conversation_id": str(conversation.id),
        "message_id": message_id,
        "last_message_id": str(replacement_last_message.id) if replacement_last_message else None,
    }


def mark_conversation_read(*, conversation, user):
    participant = ensure_user_in_conversation(user, conversation)
    last_message = conversation.messages.order_by("-created_at").first()
    participant.last_read_message = last_message
    participant.last_read_at = timezone.now()
    participant.save(update_fields=["last_read_message", "last_read_at"])

    now = timezone.now()
    incoming_message_ids = list(
        Message.objects.filter(conversation_id=conversation.id)
        .exclude(sender_id=user.id)
        .values_list("id", flat=True)
    )
    existing_receipt_message_ids = set(
        MessageReceipt.objects.filter(
            message_id__in=incoming_message_ids,
            user_id=user.id,
        ).values_list("message_id", flat=True)
    )
    missing_message_ids = [message_id for message_id in incoming_message_ids if message_id not in existing_receipt_message_ids]
    if missing_message_ids:
        MessageReceipt.objects.bulk_create(
            [
                MessageReceipt(
                    message_id=message_id,
                    user_id=user.id,
                    delivered_at=now,
                    seen_at=now,
                )
                for message_id in missing_message_ids
            ],
            ignore_conflicts=True,
        )
    changed_message_ids = list(
        MessageReceipt.objects.filter(
            message_id__in=incoming_message_ids,
            user_id=user.id,
            seen_at__isnull=True,
        ).values_list("message_id", flat=True)
    )
    MessageReceipt.objects.filter(
        message_id__in=incoming_message_ids,
        user_id=user.id,
        seen_at__isnull=True,
    ).update(
        delivered_at=Coalesce(F("delivered_at"), Value(now)),
        seen_at=now,
    )

    bump_chat_list_cache_version([user.id])
    participant._changed_message_ids = changed_message_ids
    return participant


def mark_conversation_delivered(*, conversation, user):
    ensure_user_in_conversation(user, conversation)
    now = timezone.now()
    incoming_message_ids = list(
        Message.objects.filter(conversation_id=conversation.id)
        .exclude(sender_id=user.id)
        .values_list("id", flat=True)
    )
    existing_receipt_message_ids = set(
        MessageReceipt.objects.filter(
            message_id__in=incoming_message_ids,
            user_id=user.id,
        ).values_list("message_id", flat=True)
    )
    missing_message_ids = [message_id for message_id in incoming_message_ids if message_id not in existing_receipt_message_ids]
    if missing_message_ids:
        MessageReceipt.objects.bulk_create(
            [
                MessageReceipt(
                    message_id=message_id,
                    user_id=user.id,
                    delivered_at=now,
                )
                for message_id in missing_message_ids
            ],
            ignore_conflicts=True,
        )
    changed_message_ids = list(
        MessageReceipt.objects.filter(
            message_id__in=incoming_message_ids,
            user_id=user.id,
            delivered_at__isnull=True,
        ).values_list("message_id", flat=True)
    )
    MessageReceipt.objects.filter(
        message_id__in=incoming_message_ids,
        user_id=user.id,
        delivered_at__isnull=True,
    ).update(delivered_at=now)
    return changed_message_ids


def mark_message_delivered_for_user(*, message, user):
    if message.sender_id == user.id:
        return False
    now = timezone.now()
    receipt, _ = MessageReceipt.objects.get_or_create(
        message_id=message.id,
        user_id=user.id,
        defaults={"delivered_at": now},
    )
    if receipt.delivered_at:
        return False
    receipt.delivered_at = now
    receipt.save(update_fields=["delivered_at", "updated_at"])
    return True
