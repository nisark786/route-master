import pytest
from rest_framework.exceptions import PermissionDenied

from apps.chats.models import Conversation
from apps.chats.services import (
    create_message,
    get_accessible_contacts_for_user,
    get_or_create_conversation,
    mark_conversation_read,
)


@pytest.mark.django_db
def test_get_or_create_conversation_is_idempotent_for_driver_chat(company_admin_user, driver_user):
    conversation, created = get_or_create_conversation(
        request_user=company_admin_user,
        target_user=driver_user,
        conversation_type=Conversation.TYPE_DRIVER,
    )
    second_conversation, second_created = get_or_create_conversation(
        request_user=company_admin_user,
        target_user=driver_user,
        conversation_type=Conversation.TYPE_DRIVER,
    )

    assert created is True
    assert second_created is False
    assert second_conversation.id == conversation.id
    assert conversation.participants.count() == 2


@pytest.mark.django_db
def test_get_or_create_conversation_rejects_cross_company_driver_target(company_admin_user, driver_user):
    driver_user.company = None
    driver_user.save(update_fields=["company"])

    with pytest.raises(PermissionDenied):
        get_or_create_conversation(
            request_user=company_admin_user,
            target_user=driver_user,
            conversation_type=Conversation.TYPE_DRIVER,
        )


@pytest.mark.django_db
def test_create_message_updates_conversation_and_sender_read_marker(company_admin_user, driver_user):
    conversation, _ = get_or_create_conversation(
        request_user=company_admin_user,
        target_user=driver_user,
        conversation_type=Conversation.TYPE_DRIVER,
    )

    message = create_message(
        conversation=conversation,
        sender=company_admin_user,
        content="  Hello driver  ",
    )
    sender_participant = conversation.participants.get(user=company_admin_user)

    assert message.content == "Hello driver"
    assert sender_participant.last_read_message_id == message.id
    assert conversation.last_message_at == message.created_at


@pytest.mark.django_db
def test_mark_conversation_read_updates_last_read(company_admin_user, driver_user):
    conversation, _ = get_or_create_conversation(
        request_user=company_admin_user,
        target_user=driver_user,
        conversation_type=Conversation.TYPE_DRIVER,
    )
    message = create_message(
        conversation=conversation,
        sender=company_admin_user,
        content="Hello driver",
    )

    participant = mark_conversation_read(conversation=conversation, user=driver_user)

    assert participant.last_read_message_id == message.id
    assert participant.last_read_at is not None


@pytest.mark.django_db
def test_get_accessible_contacts_for_user_returns_expected_contacts(
    company_admin_user,
    driver_user,
    super_admin_user,
):
    driver_contacts = list(get_accessible_contacts_for_user(company_admin_user))
    admin_contacts = list(get_accessible_contacts_for_user(company_admin_user, scope="administration"))

    assert any(contact["id"] == driver_user.id for contact in driver_contacts)
    assert any(contact["id"] == super_admin_user.id for contact in admin_contacts)
