from datetime import timedelta

import pytest
from django.utils import timezone

from apps.billing.models import CompanySubscription
from apps.company.serializers import CompanyProfileSerializer


@pytest.mark.django_db
def test_company_profile_serializer_returns_none_when_subscription_missing(company):
    payload = CompanyProfileSerializer(company).data

    assert payload["subscription"] is None


@pytest.mark.django_db
def test_company_profile_serializer_returns_subscription_details(company, subscription_plan):
    CompanySubscription.objects.create(
        company=company,
        plan=subscription_plan,
        end_date=timezone.now() + timedelta(days=30),
        amount_paid="999.00",
        is_active=True,
    )

    payload = CompanyProfileSerializer(company).data

    assert payload["subscription"]["plan_code"] == subscription_plan.code
    assert payload["subscription"]["amount_paid"] == "999.00"
