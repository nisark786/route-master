import pytest
from rest_framework import status


VEHICLES_URL = "/api/company-admin/vehicles/"
DASHBOARD_URL = "/api/company-admin/dashboard/overview/"


@pytest.mark.django_db
def test_company_admin_vehicle_list_requires_authentication(api_client):
    response = api_client.get(VEHICLES_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_company_admin_vehicle_list_returns_company_vehicles(auth_client, company_admin_user, vehicle):
    client = auth_client(company_admin_user)

    response = client.get(VEHICLES_URL)

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 1
    assert response.data[0]["id"] == str(vehicle.id)
    assert response.data[0]["number_plate"] == vehicle.number_plate


@pytest.mark.django_db
def test_company_admin_dashboard_overview_returns_operational_summary(
    auth_client,
    company_admin_user,
    driver_profile,
    vehicle,
    shop,
    route,
    product,
    driver_assignment,
):
    client = auth_client(company_admin_user)

    response = client.get(DASHBOARD_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["success"] is True
    assert response.data["data"]["kpis"]["drivers"] == 1
    assert response.data["data"]["kpis"]["vehicles"] == 1
    assert response.data["data"]["kpis"]["shops"] == 1
    assert response.data["data"]["kpis"]["products"] == 1
    assert response.data["data"]["kpis"]["routes"] == 1
    assert "assignment_status" in response.data["data"]
    assert "operations" in response.data["data"]
    assert "alerts" in response.data["data"]
