import logging

from celery import shared_task

from apps.chats.push_service import send_chat_push_for_message

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="chats.send_chat_message_push")
def send_chat_message_push_task(self, message_id):
    try:
        return send_chat_push_for_message(message_id=message_id)
    except Exception:
        logger.exception("Failed to send chat push for message_id=%s", message_id)
        raise
