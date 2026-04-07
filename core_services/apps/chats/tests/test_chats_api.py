import pytest
from rest_framework import status

from apps.chats.models import Message
from apps.chats.services import create_message, get_or_create_conversation


CONVERSATIONS_URL = "/api/chat/conversations/"


@pytest.mark.django_db
def test_chat_conversation_list_requires_authentication(api_client):
    response = api_client.get(CONVERSATIONS_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_chat_conversation_list_returns_accessible_contacts_for_company_admin(
    auth_client,
    company_admin_user,
    driver_user,
):
    client = auth_client(company_admin_user)

    response = client.get(CONVERSATIONS_URL, {"scope": "drivers"})

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert response.data["data"]["conversations"] == []
    assert len(response.data["data"]["contacts"]) == 1
    assert response.data["data"]["contacts"][0]["id"] == str(driver_user.id)

