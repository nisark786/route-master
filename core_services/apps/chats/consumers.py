import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from apps.chats.models import ConversationParticipant
from apps.chats.serializers import MessageSerializer
from apps.chats.services import (
    annotate_messages_with_receipt_counts,
    create_message,
    get_conversation_ids_for_user,
    mark_conversation_delivered,
    mark_message_delivered_for_user,
    register_chat_socket_connection,
    unregister_chat_socket_connection,
)


@database_sync_to_async
def _get_participant(conversation_id, user_id):
    return (
        ConversationParticipant.objects.select_related("conversation", "user")
        .filter(conversation_id=conversation_id, user_id=user_id)
        .first()
    )


@database_sync_to_async
def _persist_message(conversation, sender, content):
    message = create_message(conversation=conversation, sender=sender, content=content)
    message = annotate_messages_with_receipt_counts(
        conversation.messages.select_related("sender").filter(id=message.id)
    ).first()
    return MessageSerializer(message).data


@database_sync_to_async
def _mark_conversation_delivered(conversation, user):
    changed_message_ids = mark_conversation_delivered(conversation=conversation, user=user)
    if not changed_message_ids:
        return []
    messages = annotate_messages_with_receipt_counts(
        conversation.messages.select_related("sender").filter(id__in=changed_message_ids)
    )
    return [MessageSerializer(message).data for message in messages]


@database_sync_to_async
def _mark_message_delivered(conversation, message_id, user):
    message = conversation.messages.select_related("sender").filter(id=message_id).first()
    if not message:
        return None
    changed = mark_message_delivered_for_user(message=message, user=user)
    if not changed:
        return None
    message = annotate_messages_with_receipt_counts(
        conversation.messages.select_related("sender").filter(id=message.id)
    ).first()
    return MessageSerializer(message).data


@database_sync_to_async
def _register_presence(user):
    snapshot = register_chat_socket_connection(user)
    conversation_ids = get_conversation_ids_for_user(user)
    return snapshot, [str(conversation_id) for conversation_id in conversation_ids]


@database_sync_to_async
def _unregister_presence(user):
    snapshot = unregister_chat_socket_connection(user)
    conversation_ids = get_conversation_ids_for_user(user)
    return snapshot, [str(conversation_id) for conversation_id in conversation_ids]


class ConversationChatConsumer(AsyncWebsocketConsumer):
    async def _broadcast_presence(self, snapshot, conversation_ids):
        if not snapshot.get("changed"):
            return
        payload = {
            "event": "presence",
            "user_id": snapshot.get("user_id"),
            "is_online": bool(snapshot.get("is_online", False)),
            "last_seen_at": (
                snapshot.get("last_seen_at").isoformat() if snapshot.get("last_seen_at") else None
            ),
        }
        for conversation_id in conversation_ids:
            await self.channel_layer.group_send(
                f"chat_conversation_{conversation_id}",
                {
                    "type": "chat_message",
                    "payload": payload,
                },
            )

    async def connect(self):
        user = self.scope.get("user")
        if not user or not getattr(user, "is_authenticated", False):
            await self.close(code=4401)
            return

        self.conversation_id = str(self.scope["url_route"]["kwargs"]["conversation_id"])
        participant = await _get_participant(self.conversation_id, user.id)
        if not participant:
            await self.close(code=4403)
            return

        self.user = user
        self.conversation = participant.conversation
        self.group_name = f"chat_conversation_{self.conversation_id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        snapshot, conversation_ids = await _register_presence(self.user)
        await self._broadcast_presence(snapshot, conversation_ids)
        delivered_updates = await _mark_conversation_delivered(self.conversation, self.user)
        for updated_message in delivered_updates:
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat_message",
                    "payload": {
                        "event": "message_updated",
                        "conversation_id": self.conversation_id,
                        "message": updated_message,
                    },
                },
            )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        if hasattr(self, "user"):
            snapshot, conversation_ids = await _unregister_presence(self.user)
            await self._broadcast_presence(snapshot, conversation_ids)

    async def receive(self, text_data=None, bytes_data=None):
        if not text_data:
            return
        try:
            payload = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({"event": "error", "message": "Invalid JSON payload."}))
            return

        if payload.get("event") == "typing":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat_message",
                    "payload": {
                        "event": "typing",
                        "conversation_id": self.conversation_id,
                        "user_id": str(self.user.id),
                        "is_typing": bool(payload.get("is_typing", False)),
                    },
                },
            )
            return

        if payload.get("event") == "recording":
            await self.channel_layer.group_send(
                self.group_name,
                {
                    "type": "chat_message",
                    "payload": {
                        "event": "recording",
                        "conversation_id": self.conversation_id,
                        "user_id": str(self.user.id),
                        "is_recording": bool(payload.get("is_recording", False)),
                    },
                },
            )
            return

        content = str(payload.get("content") or "").strip()
        if not content:
            await self.send(text_data=json.dumps({"event": "error", "message": "Message content is required."}))
            return

        message = await _persist_message(self.conversation, self.user, content)
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat_message",
                "payload": {
                    "event": "message",
                    "conversation_id": self.conversation_id,
                    "message": message,
                },
            },
        )

    async def chat_message(self, event):
        payload = event.get("payload", {})
        await self.send(text_data=json.dumps(payload))
        if payload.get("event") != "message":
            return
        message = payload.get("message") or {}
        if message.get("sender_id") == str(self.user.id):
            return
        updated_message = await _mark_message_delivered(self.conversation, message.get("id"), self.user)
        if not updated_message:
            return
        await self.channel_layer.group_send(
            self.group_name,
            {
                "type": "chat_message",
                "payload": {
                    "event": "message_updated",
                    "conversation_id": self.conversation_id,
                    "message": updated_message,
                },
            },
        )
