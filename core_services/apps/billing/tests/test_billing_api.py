import pytest
from rest_framework import status


PLANS_URL = "/api/billing/plans/"


@pytest.mark.django_db
def test_subscription_plan_list_returns_active_plans(api_client, subscription_plan):
    response = api_client.get(PLANS_URL)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["code"] == subscription_plan.code

