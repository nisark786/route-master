import pytest
from rest_framework.test import APIRequestFactory

from apps.authentication.serializers import ChangeInitialPasswordSerializer, LoginSerializer


@pytest.mark.django_db
def test_login_serializer_accepts_email_identifier(company_admin_user):
    serializer = LoginSerializer(
        data={"identifier": company_admin_user.email.upper(), "password": "StrongPass123"}
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["user"] == company_admin_user


@pytest.mark.django_db
def test_login_serializer_normalizes_mobile_identifier(company_admin_user):
    serializer = LoginSerializer(
        data={"identifier": "98765-43210", "password": "StrongPass123"}
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["user"] == company_admin_user


@pytest.mark.django_db
def test_login_serializer_rejects_missing_identifier():
    serializer = LoginSerializer(data={"password": "StrongPass123"})

    assert not serializer.is_valid()
    assert "Identifier and password are required." in str(serializer.errors)


@pytest.mark.django_db
def test_login_serializer_rejects_inactive_user(company_admin_user):
    company_admin_user.is_active = False
    company_admin_user.save(update_fields=["is_active"])

    serializer = LoginSerializer(
        data={"identifier": company_admin_user.email, "password": "StrongPass123"}
    )

    assert not serializer.is_valid()
    assert "Account is inactive." in str(serializer.errors)


@pytest.mark.django_db
def test_change_initial_password_serializer_rejects_mismatch(first_login_user):
    request = APIRequestFactory().post("/api/auth/change-initial-password/")
    request.user = first_login_user
    serializer = ChangeInitialPasswordSerializer(
        data={
            "current_password": "TempPass123",
            "new_password": "NewStrongPass123",
            "confirm_password": "DifferentPass123",
        },
        context={"request": request},
    )

    assert not serializer.is_valid()
    assert "confirm_password" in serializer.errors


@pytest.mark.django_db
def test_change_initial_password_serializer_rejects_same_password(first_login_user):
    request = APIRequestFactory().post("/api/auth/change-initial-password/")
    request.user = first_login_user
    serializer = ChangeInitialPasswordSerializer(
        data={
            "current_password": "TempPass123",
            "new_password": "TempPass123",
            "confirm_password": "TempPass123",
        },
        context={"request": request},
    )

    assert not serializer.is_valid()
    assert "new_password" in serializer.errors


@pytest.mark.django_db
def test_change_initial_password_serializer_accepts_valid_payload(first_login_user):
    request = APIRequestFactory().post("/api/auth/change-initial-password/")
    request.user = first_login_user
    serializer = ChangeInitialPasswordSerializer(
        data={
            "current_password": "TempPass123",
            "new_password": "NewStrongPass123",
            "confirm_password": "NewStrongPass123",
        },
        context={"request": request},
    )

    assert serializer.is_valid(), serializer.errors
