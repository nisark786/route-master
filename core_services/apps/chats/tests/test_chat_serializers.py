import pytest
from rest_framework.test import APIRequestFactory

from apps.chats.models import Conversation
from apps.chats.serializers import ConversationSerializer, ConversationStartSerializer
from apps.chats.services import create_message, get_or_create_conversation


@pytest.mark.django_db
def test_conversation_start_serializer_resolves_target_user(driver_user):
    serializer = ConversationStartSerializer(
        data={
            "conversation_type": Conversation.TYPE_DRIVER,
            "target_user_id": str(driver_user.id),
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["target_user_id"] == driver_user


@pytest.mark.django_db
def test_conversation_start_serializer_rejects_missing_target_user():
    serializer = ConversationStartSerializer(
        data={
            "conversation_type": Conversation.TYPE_DRIVER,
            "target_user_id": "0db7f3f8-bec5-4ef1-a7af-7d885d8a7aa0",
        }
    )

    assert not serializer.is_valid()
    assert "target_user_id" in serializer.errors


@pytest.mark.django_db
def test_conversation_serializer_computes_unread_count(company_admin_user, driver_user):
    conversation, _ = get_or_create_conversation(
        request_user=company_admin_user,
        target_user=driver_user,
        conversation_type=Conversation.TYPE_DRIVER,
    )
    create_message(conversation=conversation, sender=company_admin_user, content="First")
    create_message(conversation=conversation, sender=company_admin_user, content="Second")

    request = APIRequestFactory().get("/api/chat/conversations/")
    request.user = driver_user
    serialized = ConversationSerializer(conversation, context={"request": request}).data

    assert serialized["last_message"]["content"] == "Second"
    assert serialized["unread_count"] == 2
