import pytest
from rest_framework import status


PROFILE_URL = "/api/company/profile/"


@pytest.mark.django_db
def test_company_profile_requires_authentication(api_client):
    response = api_client.get(PROFILE_URL)

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
def test_company_profile_returns_company_data(auth_client, company_admin_user):
    client = auth_client(company_admin_user)

    response = client.get(PROFILE_URL)

    assert response.status_code == status.HTTP_200_OK
    assert response.data["name"] == company_admin_user.company.name
    assert response.data["official_email"] == company_admin_user.company.official_email

