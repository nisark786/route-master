import pytest
from rest_framework import status


DASHBOARD_URL = "/api/shop-owner/dashboard/"


@pytest.mark.django_db
def test_shop_owner_dashboard_requires_authentication(api_client):
    response = api_client.get(DASHBOARD_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_shop_owner_dashboard_returns_metrics(auth_client, shop_owner_user, shop):
    client = auth_client(shop_owner_user)

    response = client.get(DASHBOARD_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert response.data["data"]["metrics"]["open_deliveries"] == 0
    assert response.data["data"]["recent_invoices"] == []

