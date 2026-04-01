import logging
from pathlib import Path

import firebase_admin
from django.conf import settings
from firebase_admin import credentials, messaging

from apps.chats.models import DevicePushToken, Message

logger = logging.getLogger(__name__)
_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app:
        return _firebase_app

    credentials_file = (getattr(settings, "FIREBASE_CREDENTIALS_FILE", "") or "").strip()
    if not credentials_file:
        return None

    credentials_path = Path(credentials_file)
    if not credentials_path.exists():
        logger.warning("Firebase credentials file not found: %s", credentials_path)
        return None

    options = {}
    project_id = (getattr(settings, "FIREBASE_PROJECT_ID", "") or "").strip()
    if project_id:
        options["projectId"] = project_id
    cred = credentials.Certificate(str(credentials_path))
    _firebase_app = firebase_admin.initialize_app(cred, options=options or None, name="route_master_chat_push")
    return _firebase_app


def _build_push_body(message):
    if message.message_type == Message.TYPE_VOICE:
        return "Voice message"
    content = (message.content or "").strip()
    if not content:
        return "New message"
    return content[:160]


def _resolve_sender_title(message):
    sender = getattr(message, "sender", None)
    if not sender:
        return "Route Master"
    if getattr(sender, "role", "") == "COMPANY_ADMIN":
        company_name = (getattr(getattr(sender, "company", None), "name", "") or "").strip()
        if company_name:
            return company_name
    return (getattr(sender, "email", "") or "Route Master").strip()


def send_chat_push_for_message(*, message_id):
    if not getattr(settings, "CHAT_PUSH_ENABLED", False):
        return {"sent": 0, "tokens": 0, "reason": "chat_push_disabled"}

    app = _get_firebase_app()
    if not app:
        return {"sent": 0, "tokens": 0, "reason": "firebase_not_configured"}

    message = (
        Message.objects.select_related("sender", "sender__company", "conversation")
        .filter(id=message_id)
        .first()
    )
    if not message or not message.sender_id:
        return {"sent": 0, "tokens": 0, "reason": "message_not_found"}

    recipient_ids = list(
        message.conversation.participants.exclude(user_id=message.sender_id).values_list("user_id", flat=True)
    )
    if not recipient_ids:
        return {"sent": 0, "tokens": 0, "reason": "no_recipients"}

    token_rows = list(
        DevicePushToken.objects.filter(user_id__in=recipient_ids, is_active=True)
        .values("id", "token")
    )
    if not token_rows:
        return {"sent": 0, "tokens": 0, "reason": "no_active_tokens"}

    tokens = [row["token"] for row in token_rows]
    token_id_by_token = {row["token"]: row["id"] for row in token_rows}
    sender_name = _resolve_sender_title(message)
    body = _build_push_body(message)

    multicast = messaging.MulticastMessage(
        notification=messaging.Notification(title=sender_name, body=body),
        data={
            "type": "chat_message",
            "conversation_id": str(message.conversation_id),
            "message_id": str(message.id),
            "chat_message_type": message.message_type,
        },
        android=messaging.AndroidConfig(priority="high"),
        tokens=tokens,
    )
    response = messaging.send_each_for_multicast(multicast, app=app)

    invalid_token_ids = []
    for index, item in enumerate(response.responses):
        if item.success:
            continue
        token = tokens[index]
        error_code = str(getattr(item.exception, "code", "") or "").lower()
        logger.warning(
            "Chat push failed: message=%s token_suffix=%s code=%s error=%s",
            message.id,
            token[-10:] if len(token) > 10 else token,
            error_code,
            str(item.exception),
        )
        if (
            "registration-token-not-registered" in error_code
            or "invalid-registration-token" in error_code
            or "unregistered" in error_code
        ):
            token_id = token_id_by_token.get(token)
            if token_id:
                invalid_token_ids.append(token_id)

    if invalid_token_ids:
        DevicePushToken.objects.filter(id__in=invalid_token_ids).update(is_active=False)

    logger.info(
        "Chat push sent: message=%s success=%s failure=%s tokens=%s",
        message.id,
        response.success_count,
        response.failure_count,
        len(tokens),
    )
    return {
        "sent": response.success_count,
        "failed": response.failure_count,
        "tokens": len(tokens),
    }
