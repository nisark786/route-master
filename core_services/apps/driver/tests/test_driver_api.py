import pytest
from rest_framework import status


ASSIGNMENTS_URL = "/api/driver/assignments/"


@pytest.mark.django_db
def test_driver_assignment_list_requires_authentication(api_client):
    response = api_client.get(ASSIGNMENTS_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_driver_assignment_list_returns_driver_assignments(auth_client, driver_user, driver_profile, driver_assignment, route_shop):
    client = auth_client(driver_user)

    response = client.get(ASSIGNMENTS_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert len(response.data["data"]) == 1
    assert response.data["data"][0]["id"] == str(driver_assignment.id)

