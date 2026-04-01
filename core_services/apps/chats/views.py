from django.core.cache import cache
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.chats.models import Conversation
from apps.chats.models import Message
from apps.chats.serializers import (
    ConversationSerializer,
    ConversationStartSerializer,
    MessageCreateSerializer,
    MessageSerializer,
    MessageUpdateSerializer,
    PushTokenRegisterSerializer,
    PushTokenUnregisterSerializer,
    VoiceMessageCreateSerializer,
)
from apps.chats.services import (
    annotate_messages_with_receipt_counts,
    create_message,
    create_voice_message,
    delete_message,
    ensure_user_in_conversation,
    get_accessible_contacts_for_user,
    get_accessible_conversations_for_user,
    get_chat_list_cache_version,
    get_presence_snapshot_for_users,
    get_or_create_conversation,
    mark_conversation_delivered,
    mark_conversation_read,
    register_device_push_token,
    unregister_device_push_token,
    update_message,
)
from apps.core.permissions import HasPermissionCode


class ChatAPIView(APIView):
    permission_classes = [IsAuthenticated, HasPermissionCode]
    required_any_permissions = ["company_admin.access", "main_admin.access", "driver.access"]

    def success_response(self, data=None, message="Request completed successfully.", status_code=status.HTTP_200_OK):
        return Response({"success": True, "message": message, "data": data}, status=status_code)

    @staticmethod
    def broadcast_to_conversation(conversation_id, payload):
        channel_layer = get_channel_layer()
        if not channel_layer:
            return
        async_to_sync(channel_layer.group_send)(
            f"chat_conversation_{conversation_id}",
            {
                "type": "chat_message",
                "payload": payload,
            },
        )

    def _broadcast_message_updates(self, conversation, message_ids):
        if not message_ids:
            return
        messages = annotate_messages_with_receipt_counts(
            conversation.messages.select_related("sender").filter(id__in=message_ids)
        )
        for message in messages:
            self.broadcast_to_conversation(
                conversation.id,
                {
                    "event": "message_updated",
                    "conversation_id": str(conversation.id),
                    "message": MessageSerializer(message).data,
                },
            )


class ConversationListAPIView(ChatAPIView):
    @swagger_auto_schema(
        tags=["Chats"],
        operation_summary="List accessible conversations",
        manual_parameters=[
            openapi.Parameter("scope", openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
        ],
    )
    def get(self, request):
        scope = (request.query_params.get("scope") or "").strip().lower()
        cache_key = f"chat:list:{request.user.id}:{scope or 'all'}:v{get_chat_list_cache_version(request.user.id)}"
        cached = cache.get(cache_key)
        if cached is not None:
            return self.success_response(data=cached, message="Conversations loaded.")

        conversations = list(get_accessible_conversations_for_user(request.user, scope=scope))
        conversation_rows = [
            {
                "id": str(conversation.id),
                "conversation_type": conversation.conversation_type,
                "company_id": str(conversation.company_id) if conversation.company_id else None,
                "created_at": conversation.created_at,
                "updated_at": conversation.updated_at,
                "last_message_at": conversation.last_message_at,
                "counterpart_user_id": str(conversation.counterpart_user_id) if getattr(conversation, "counterpart_user_id", None) else None,
                "last_message": (
                    {
                        "id": str(conversation._last_message_id),
                        "message_type": conversation._last_message_type,
                        "content": conversation._last_message_content,
                        "created_at": conversation._last_message_created_at,
                        "updated_at": conversation._last_message_updated_at,
                        "sender_id": str(conversation._last_message_sender_id) if conversation._last_message_sender_id else None,
                        "sender_email": conversation._last_message_sender_email,
                        "sender_role": conversation._last_message_sender_role,
                        "is_edited": bool(
                            conversation._last_message_updated_at
                            and conversation._last_message_created_at
                            and conversation._last_message_updated_at > conversation._last_message_created_at
                        ),
                    }
                    if getattr(conversation, "_last_message_id", None)
                    else None
                ),
                "unread_count": int(getattr(conversation, "_annotated_unread_count", 0) or 0),
            }
            for conversation in conversations
        ]
        contact_rows = list(get_accessible_contacts_for_user(request.user, scope=scope))
        presence_map = get_presence_snapshot_for_users([row.get("id") for row in contact_rows])
        contacts = [
            {
                "id": str(user["id"]),
                "display_name": self._get_contact_display_name(user),
                "email": user.get("email"),
                "mobile_number": user.get("mobile_number"),
                "role": user.get("role"),
                "company_id": str(user["company_id"]) if user.get("company_id") else None,
                "is_online": bool(presence_map.get(str(user["id"]), {}).get("is_online", False)),
                "last_seen_at": presence_map.get(str(user["id"]), {}).get("last_seen_at"),
            }
            for user in contact_rows
        ]
        payload = {"conversations": conversation_rows, "contacts": contacts}
        cache.set(cache_key, payload, timeout=30)
        return self.success_response(data=payload, message="Conversations loaded.")

    @staticmethod
    def _get_contact_display_name(user):
        if user.get("role") == "COMPANY_ADMIN":
            company_name = (user.get("company__name") or "").strip()
            if company_name:
                return company_name
        display_name = user.get("driver_profile__name")
        if display_name:
            return display_name
        return user.get("email") or user.get("mobile_number") or str(user.get("id"))


class ConversationStartAPIView(ChatAPIView):
    @swagger_auto_schema(
        tags=["Chats"],
        operation_summary="Start or load a conversation",
        request_body=ConversationStartSerializer,
    )
    def post(self, request):
        serializer = ConversationStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        conversation, created = get_or_create_conversation(
            request_user=request.user,
            target_user=payload["target_user_id"],
            conversation_type=payload["conversation_type"],
        )
        data = ConversationSerializer(conversation, context={"request": request}).data
        return self.success_response(
            data=data,
            message="Conversation created." if created else "Conversation loaded.",
            status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ConversationMessageListCreateAPIView(ChatAPIView):
    @swagger_auto_schema(tags=["Chats"], operation_summary="List conversation messages")
    def get(self, request, conversation_id):
        conversation = Conversation.objects.prefetch_related("participants__user").filter(id=conversation_id).first()
        if not conversation:
            return Response({"success": False, "message": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        ensure_user_in_conversation(request.user, conversation)
        delivered_message_ids = mark_conversation_delivered(conversation=conversation, user=request.user)
        messages = annotate_messages_with_receipt_counts(
            conversation.messages.select_related("sender").order_by("created_at")
        )
        self._broadcast_message_updates(conversation, delivered_message_ids)
        return self.success_response(
            data=MessageSerializer(messages, many=True, context={"request": request}).data,
            message="Messages loaded.",
        )

    @swagger_auto_schema(
        tags=["Chats"],
        operation_summary="Send a conversation message",
        request_body=MessageCreateSerializer,
    )
    def post(self, request, conversation_id):
        conversation = Conversation.objects.prefetch_related("participants__user").filter(id=conversation_id).first()
        if not conversation:
            return Response({"success": False, "message": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        ensure_user_in_conversation(request.user, conversation)

        serializer = MessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        message = create_message(
            conversation=conversation,
            sender=request.user,
            content=serializer.validated_data["content"],
        )
        message = annotate_messages_with_receipt_counts(
            Message.objects.select_related("sender").filter(id=message.id)
        ).first()
        payload = MessageSerializer(message, context={"request": request}).data

        channel_layer = get_channel_layer()
        if channel_layer:
            self.broadcast_to_conversation(
                conversation.id,
                {
                    "event": "message",
                    "conversation_id": str(conversation.id),
                    "message": payload,
                },
            )

        return self.success_response(
            data=payload,
            message="Message sent.",
            status_code=status.HTTP_201_CREATED,
        )


class ConversationVoiceMessageCreateAPIView(ChatAPIView):
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        tags=["Chats"],
        operation_summary="Send a voice message",
        request_body=VoiceMessageCreateSerializer,
    )
    def post(self, request, conversation_id):
        conversation = Conversation.objects.prefetch_related("participants__user").filter(id=conversation_id).first()
        if not conversation:
            return Response({"success": False, "message": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        ensure_user_in_conversation(request.user, conversation)

        serializer = VoiceMessageCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        message = create_voice_message(
            conversation=conversation,
            sender=request.user,
            audio_file=payload["audio"],
            duration_ms=payload.get("duration_ms"),
        )
        message = annotate_messages_with_receipt_counts(
            Message.objects.select_related("sender").filter(id=message.id)
        ).first()
        serialized_message = MessageSerializer(message, context={"request": request}).data
        self.broadcast_to_conversation(
            conversation.id,
            {
                "event": "message",
                "conversation_id": str(conversation.id),
                "message": serialized_message,
            },
        )
        return self.success_response(
            data=serialized_message,
            message="Voice message sent.",
            status_code=status.HTTP_201_CREATED,
        )


class ConversationReadAPIView(ChatAPIView):
    @swagger_auto_schema(tags=["Chats"], operation_summary="Mark a conversation as read")
    def post(self, request, conversation_id):
        conversation = Conversation.objects.filter(id=conversation_id).first()
        if not conversation:
            return Response({"success": False, "message": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)
        ensure_user_in_conversation(request.user, conversation)
        participant = mark_conversation_read(conversation=conversation, user=request.user)
        changed_message_ids = getattr(participant, "_changed_message_ids", [])
        self._broadcast_message_updates(conversation, changed_message_ids)
        return self.success_response(
            data={
                "conversation_id": str(conversation.id),
                "last_read_at": participant.last_read_at,
                "last_read_message_id": str(participant.last_read_message_id) if participant.last_read_message_id else None,
            },
            message="Conversation marked as read.",
        )


class ConversationMessageDetailAPIView(ChatAPIView):
    @swagger_auto_schema(
        tags=["Chats"],
        operation_summary="Update a sent message",
        request_body=MessageUpdateSerializer,
    )
    def patch(self, request, conversation_id, message_id):
        conversation = Conversation.objects.prefetch_related("participants__user").filter(id=conversation_id).first()
        if not conversation:
            return Response({"success": False, "message": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

        message = conversation.messages.select_related("sender").filter(id=message_id).first()
        if not message:
            return Response({"success": False, "message": "Message not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = MessageUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        updated_message = update_message(
            conversation=conversation,
            message=message,
            user=request.user,
            content=serializer.validated_data["content"],
        )
        updated_message = annotate_messages_with_receipt_counts(
            Message.objects.select_related("sender").filter(id=updated_message.id)
        ).first()
        payload = MessageSerializer(updated_message, context={"request": request}).data
        self.broadcast_to_conversation(
            conversation.id,
            {
                "event": "message_updated",
                "conversation_id": str(conversation.id),
                "message": payload,
            },
        )
        return self.success_response(data=payload, message="Message updated.")

    @swagger_auto_schema(
        tags=["Chats"],
        operation_summary="Delete a sent message",
    )
    def delete(self, request, conversation_id, message_id):
        conversation = Conversation.objects.prefetch_related("participants__user").filter(id=conversation_id).first()
        if not conversation:
            return Response({"success": False, "message": "Conversation not found."}, status=status.HTTP_404_NOT_FOUND)

        message = conversation.messages.select_related("sender").filter(id=message_id).first()
        if not message:
            return Response({"success": False, "message": "Message not found."}, status=status.HTTP_404_NOT_FOUND)

        payload = delete_message(
            conversation=conversation,
            message=message,
            user=request.user,
        )
        self.broadcast_to_conversation(
            conversation.id,
            {
                "event": "message_deleted",
                **payload,
            },
        )
        return self.success_response(data=payload, message="Message deleted.")


class PushTokenRegisterAPIView(ChatAPIView):
    @swagger_auto_schema(
        tags=["Chats"],
        operation_summary="Register device push token",
        request_body=PushTokenRegisterSerializer,
    )
    def post(self, request):
        serializer = PushTokenRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data
        row = register_device_push_token(
            user=request.user,
            token=payload["token"],
            platform=payload.get("platform"),
        )
        return self.success_response(
            data={
                "id": str(row.id),
                "platform": row.platform,
                "is_active": row.is_active,
            },
            message="Push token registered.",
            status_code=status.HTTP_201_CREATED,
        )


class PushTokenUnregisterAPIView(ChatAPIView):
    @swagger_auto_schema(
        tags=["Chats"],
        operation_summary="Unregister device push token",
        request_body=PushTokenUnregisterSerializer,
    )
    def post(self, request):
        serializer = PushTokenUnregisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        deleted = unregister_device_push_token(
            user=request.user,
            token=serializer.validated_data["token"],
        )
        return self.success_response(
            data={"unregistered": deleted},
            message="Push token unregistered.",
        )
