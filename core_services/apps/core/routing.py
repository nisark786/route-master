from django.urls import path

from apps.core.consumers import CompanyLiveTrackingConsumer
from apps.chats.consumers import ConversationChatConsumer


websocket_urlpatterns = [
    path("ws/live-tracking/company/<uuid:company_id>/", CompanyLiveTrackingConsumer.as_asgi()),
    path("ws/chat/conversations/<uuid:conversation_id>/", ConversationChatConsumer.as_asgi()),
]
