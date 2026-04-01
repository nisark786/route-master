from datetime import timedelta

import pytest
from django.contrib.auth.hashers import check_password
from django.utils import timezone

from apps.billing.models import PendingCompanyRegistration
from apps.billing.serializers import StartRegistrationSerializer, VerifyOtpSerializer
from apps.billing.services import store_registration_otp


@pytest.mark.django_db
def test_start_registration_serializer_hashes_password_and_resolves_plan(subscription_plan):
    serializer = StartRegistrationSerializer(
        data={
            "company_name": "Fresh Company",
            "official_email": "fresh@example.com",
            "phone": "9999999999",
            "address": "HQ",
            "admin_email": "owner@example.com",
            "admin_password": "StrongPass123",
            "plan_code": f" {subscription_plan.code.upper()} ",
        }
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["plan"] == subscription_plan
    assert serializer.validated_data["plan_code"] == subscription_plan.code
    assert check_password("StrongPass123", serializer.validated_data["admin_password_hash"])


@pytest.mark.django_db
def test_start_registration_serializer_rejects_existing_admin_email(subscription_plan, company_admin_user):
    serializer = StartRegistrationSerializer(
        data={
            "company_name": "Fresh Company",
            "official_email": "fresh@example.com",
            "admin_email": company_admin_user.email,
            "admin_password": "StrongPass123",
            "plan_code": subscription_plan.code,
        }
    )

    assert not serializer.is_valid()
    assert "admin_email" in serializer.errors


@pytest.mark.django_db
def test_verify_otp_serializer_accepts_valid_otp(subscription_plan):
    registration = PendingCompanyRegistration.objects.create(
        company_name="New Co",
        official_email="newco@example.com",
        admin_email="admin@newco.example",
        admin_password_hash="hashed",
        plan=subscription_plan,
        otp_expires_at=timezone.now() + timedelta(minutes=5),
    )
    store_registration_otp(registration.id, "123456")

    serializer = VerifyOtpSerializer(
        data={"registration_id": registration.id, "otp": "123456"}
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["registration"] == registration


@pytest.mark.django_db
def test_verify_otp_serializer_marks_registration_expired_when_cached_hash_missing(subscription_plan):
    registration = PendingCompanyRegistration.objects.create(
        company_name="Expire Co",
        official_email="expire@example.com",
        admin_email="admin@expire.example",
        admin_password_hash="hashed",
        plan=subscription_plan,
        otp_expires_at=timezone.now() - timedelta(minutes=1),
    )

    serializer = VerifyOtpSerializer(
        data={"registration_id": registration.id, "otp": "123456"}
    )

    assert not serializer.is_valid()
    registration.refresh_from_db()
    assert registration.status == PendingCompanyRegistration.STATUS_EXPIRED
    assert "otp" in serializer.errors
