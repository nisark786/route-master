import pytest
from rest_framework import status


OVERVIEW_URL = "/api/admin/overview/"


@pytest.mark.django_db
def test_main_admin_overview_requires_authentication(api_client):
    response = api_client.get(OVERVIEW_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_main_admin_overview_returns_dashboard_payload(auth_client, super_admin_user):
    client = auth_client(super_admin_user)

    response = client.get(OVERVIEW_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert "total_companies" in response.data["data"]
    assert "active_companies" in response.data["data"]

