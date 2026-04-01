import pytest
from django.core.cache import cache

from apps.billing.models import SubscriptionPlan
from apps.billing.services import (
    delete_registration_otp,
    generate_otp,
    generate_tokens_for_user,
    get_cached_active_plans,
    get_registration_otp_hash,
    hash_otp,
    invalidate_active_plans_cache,
    queue_registration_otp,
    store_registration_otp,
    verify_hashed_otp,
)


def test_generate_otp_returns_six_digit_string():
    otp = generate_otp()

    assert len(otp) == 6
    assert otp.isdigit()


def test_hash_and_verify_otp_round_trip():
    otp = "123456"
    hashed = hash_otp(otp)

    assert hashed != otp
    assert verify_hashed_otp(otp, hashed) is True
    assert verify_hashed_otp("000000", hashed) is False


@pytest.mark.django_db
def test_registration_otp_cache_lifecycle():
    registration_id = "abc-123"
    otp = "654321"

    store_registration_otp(registration_id, otp)
    hashed = get_registration_otp_hash(registration_id)

    assert hashed
    assert verify_hashed_otp(otp, hashed) is True

    delete_registration_otp(registration_id)

    assert get_registration_otp_hash(registration_id) is None


@pytest.mark.django_db
def test_queue_registration_otp_falls_back_to_sync_send(settings, monkeypatch):
    settings.SEND_OTP_ASYNC = True
    called = {"sync": 0}

    def fake_send(email, otp):
        called["sync"] += 1

    class DummyTask:
        @staticmethod
        def delay(email, otp):
            raise RuntimeError("broker unavailable")

    monkeypatch.setattr("apps.billing.services.send_registration_otp", fake_send)
    monkeypatch.setattr(
        "apps.billing.tasks.send_registration_otp_email_task",
        DummyTask(),
    )

    queue_registration_otp("company@example.com", "123456")

    assert called["sync"] == 1


@pytest.mark.django_db
def test_get_cached_active_plans_uses_cache():
    SubscriptionPlan.objects.create(
        code="starter",
        name="Starter",
        price="10.00",
        duration_days=30,
        is_active=True,
    )

    first = get_cached_active_plans()
    cache.delete("billing:active_plans")
    second = get_cached_active_plans()

    assert [item.code for item in first] == ["starter"]
    assert [item.code for item in second] == ["starter"]
    assert cache.get("billing:active_plans") is not None

    invalidate_active_plans_cache()
    assert cache.get("billing:active_plans") is None


@pytest.mark.django_db
def test_generate_tokens_for_user_returns_access_and_refresh(company_admin_user):
    tokens = generate_tokens_for_user(company_admin_user)

    assert "access" in tokens
    assert "refresh" in tokens
