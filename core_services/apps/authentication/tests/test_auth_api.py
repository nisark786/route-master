import pytest
from rest_framework import status

from apps.authentication.services import generate_tokens_for_user


WEB_LOGIN_URL = "/api/auth/web/login/"
MOBILE_LOGIN_URL = "/api/auth/mobile/login/"
REFRESH_URL = "/api/auth/refresh/"
LOGOUT_URL = "/api/auth/logout/"
ME_URL = "/api/auth/me/"
CHANGE_INITIAL_PASSWORD_URL = "/api/auth/change-initial-password/"


@pytest.mark.django_db
def test_web_login_sets_refresh_cookie_and_omits_refresh_body(api_client, company_admin_user):
    response = api_client.post(
        WEB_LOGIN_URL,
        {"identifier": company_admin_user.email, "password": "StrongPass123"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" not in response.data
    assert response.cookies["refresh_token"].value
    assert response.data["role"] == "COMPANY_ADMIN"
    assert str(response.data["company_id"]) == str(company_admin_user.company_id)


@pytest.mark.django_db
def test_mobile_login_returns_refresh_in_body_and_no_cookie(api_client, company_admin_user):
    response = api_client.post(
        MOBILE_LOGIN_URL,
        {"mobile_number": "98765-43210", "password": "StrongPass123"},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert "access" in response.data
    assert "refresh" in response.data
    assert "refresh_token" not in response.cookies

@pytest.mark.django_db
def test_login_throttles_after_repeated_failures(api_client, company_admin_user):
    payload = {"identifier": company_admin_user.email, "password": "WrongPass123"}
    for _ in range(5):
        response = api_client.post(WEB_LOGIN_URL, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    throttled_response = api_client.post(WEB_LOGIN_URL, payload, format="json")

    assert throttled_response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Too many failed login attempts" in throttled_response.data["message"]


@pytest.mark.django_db
def test_refresh_uses_cookie_token(api_client, company_admin_user):
    login_response = api_client.post(
        WEB_LOGIN_URL,
        {"identifier": company_admin_user.email, "password": "StrongPass123"},
        format="json",
    )

    refresh_token = login_response.cookies["refresh_token"].value
    api_client.cookies["refresh_token"] = refresh_token

    refresh_response = api_client.post(REFRESH_URL, {}, format="json")

    assert refresh_response.status_code == status.HTTP_200_OK
    assert "access" in refresh_response.data


@pytest.mark.django_db
def test_logout_blacklists_refresh_token_and_clears_cookie(api_client, company_admin_user):
    tokens = generate_tokens_for_user(company_admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = api_client.post(
        LOGOUT_URL,
        {"refresh": tokens["refresh"]},
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.cookies["refresh_token"].value == ""

    refresh_response = api_client.post(
        REFRESH_URL,
        {"refresh": tokens["refresh"]},
        format="json",
    )
    assert refresh_response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_me_returns_authenticated_user_profile_and_permissions(api_client, company_admin_user):
    tokens = generate_tokens_for_user(company_admin_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = api_client.get(ME_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["email"] == company_admin_user.email
    assert str(response.data["company_id"]) == str(company_admin_user.company_id)
    assert "company_admin.access" in response.data["permissions"]
    assert "product.create" in response.data["permissions"]


@pytest.mark.django_db
def test_change_initial_password_updates_password_and_clears_flag(api_client, first_login_user):
    tokens = generate_tokens_for_user(first_login_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = api_client.post(
        CHANGE_INITIAL_PASSWORD_URL,
        {
            "current_password": "TempPass123",
            "new_password": "NewStrongPass123",
            "confirm_password": "NewStrongPass123",
        },
        format="json",
    )

    first_login_user.refresh_from_db()

    assert response.status_code == status.HTTP_200_OK
    assert first_login_user.must_change_password is False
    assert first_login_user.check_password("NewStrongPass123")


@pytest.mark.django_db
def test_change_initial_password_rejects_wrong_current_password(api_client, first_login_user):
    tokens = generate_tokens_for_user(first_login_user)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    response = api_client.post(
        CHANGE_INITIAL_PASSWORD_URL,
        {
            "current_password": "WrongTempPass",
            "new_password": "NewStrongPass123",
            "confirm_password": "NewStrongPass123",
        },
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "current_password" in response.data["error"]["details"]
