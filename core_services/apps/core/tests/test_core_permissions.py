import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.test import APIRequestFactory

from apps.authentication.models import User
from apps.core.middlewares import TenantMiddleware
from apps.core.permissions import HasPermissionCode


class _DummyView:
    required_permission = "company_admin.access"
    required_any_permissions = None
    required_all_permissions = None
    required_permission_map = None


@pytest.mark.django_db
def test_has_permission_code_rejects_anonymous_user():
    permission = HasPermissionCode()
    request = APIRequestFactory().get("/")
    request.user = AnonymousUser()

    allowed = permission.has_permission(request, _DummyView())

    assert allowed is False


@pytest.mark.django_db
def test_has_permission_code_allows_company_admin_role(company):
    permission = HasPermissionCode()
    request = APIRequestFactory().get("/")
    request.user = User.objects.create_user(
        email="permadmin@example.com",
        password="StrongPass123",
        role="COMPANY_ADMIN",
        company=company,
        mobile_number="9000000003",
    )
    request.company_id = request.user.company_id

    allowed = permission.has_permission(request, _DummyView())

    assert allowed is True


def test_tenant_middleware_extracts_bearer_token():
    middleware = TenantMiddleware(lambda request: None)
    request = APIRequestFactory().get("/", HTTP_AUTHORIZATION="Bearer sample-token")

    token = middleware._extract_bearer_token(request)

    assert token == "sample-token"

