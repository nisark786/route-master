import pytest
from django.core.cache import cache

from apps.authentication.services import (
    _login_attempt_key,
    generate_tokens_for_user,
    get_user_cache,
    increment_login_attempt,
    invalidate_user_cache,
    is_login_allowed,
    reset_login_attempts,
)


@pytest.mark.django_db
def test_generate_tokens_for_user_includes_access_and_refresh(company_admin_user):
    tokens = generate_tokens_for_user(company_admin_user)

    assert "access" in tokens
    assert "refresh" in tokens
    assert isinstance(tokens["access"], str)
    assert isinstance(tokens["refresh"], str)


@pytest.mark.django_db
def test_login_attempt_helpers_track_and_reset_attempts():
    identifier = "USER@Example.com"

    assert is_login_allowed(identifier) is True

    for _ in range(5):
        increment_login_attempt(identifier, timeout_seconds=60)

    assert is_login_allowed(identifier) is False
    assert cache.get(_login_attempt_key(identifier)) == 5

    reset_login_attempts(identifier)

    assert is_login_allowed(identifier) is True
    assert cache.get(_login_attempt_key(identifier)) is None


@pytest.mark.django_db
def test_get_user_cache_caches_profile_data(company_admin_user):
    payload = get_user_cache(company_admin_user)
    cache_key = f"user_profile:{company_admin_user.id}"

    assert payload["email"] == company_admin_user.email
    assert cache.get(cache_key)["email"] == company_admin_user.email

    invalidate_user_cache(company_admin_user.id)

    assert cache.get(cache_key) is None
