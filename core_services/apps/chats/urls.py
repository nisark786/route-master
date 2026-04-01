from django.urls import path

from apps.chats.views import (
    ConversationListAPIView,
    ConversationMessageDetailAPIView,
    ConversationMessageListCreateAPIView,
    ConversationReadAPIView,
    ConversationStartAPIView,
    ConversationVoiceMessageCreateAPIView,
    PushTokenRegisterAPIView,
    PushTokenUnregisterAPIView,
)


urlpatterns = [
    path("conversations/", ConversationListAPIView.as_view(), name="chat-conversation-list"),
    path("conversations/start/", ConversationStartAPIView.as_view(), name="chat-conversation-start"),
    path("conversations/<uuid:conversation_id>/messages/", ConversationMessageListCreateAPIView.as_view(), name="chat-message-list-create"),
    path("conversations/<uuid:conversation_id>/voice/", ConversationVoiceMessageCreateAPIView.as_view(), name="chat-voice-message-create"),
    path(
        "conversations/<uuid:conversation_id>/messages/<uuid:message_id>/",
        ConversationMessageDetailAPIView.as_view(),
        name="chat-message-detail",
    ),
    path("conversations/<uuid:conversation_id>/read/", ConversationReadAPIView.as_view(), name="chat-conversation-read"),
    path("push/register/", PushTokenRegisterAPIView.as_view(), name="chat-push-token-register"),
    path("push/unregister/", PushTokenUnregisterAPIView.as_view(), name="chat-push-token-unregister"),
]
