from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


class TenantMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.company_id = None
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            if not user.is_platform_admin:
                request.company_id = user.company_id
            return
        token = self._extract_bearer_token(request)
        if not token:
            return

        token_claims = self._extract_token_claims(token)
        if not token_claims:
            return

        if token_claims.get("is_platform_admin") is not None:
            if not token_claims["is_platform_admin"]:
                request.company_id = token_claims["company_id"]
            return


        tenant_data = self._get_tenant_data(token_claims["user_id"])
        if tenant_data and not tenant_data["is_platform_admin"]:
            request.company_id = tenant_data["company_id"]

    def _extract_bearer_token(self, request):
        header = request.META.get("HTTP_AUTHORIZATION", "")
        if not header.startswith("Bearer "):
            return None
        return header.split(" ", 1)[1].strip()

    def _extract_token_claims(self, token):
        try:
            payload = AccessToken(token)
            role = payload.get("role")
            company_id = payload.get("company_id")
            is_platform_admin = payload.get("is_platform_admin")
            if is_platform_admin is None and role is not None:
                is_platform_admin = role == "SUPER_ADMIN"
            return {
                "user_id": payload.get("user_id"),
                "role": role,
                "company_id": company_id,
                "is_platform_admin": is_platform_admin,
            }
        except (TokenError, Exception):
            return None

    def _get_tenant_data(self, user_id):
        cache_key = f"tenant_user:{user_id}"
        cached = cache.get(cache_key)
        if cached is not None:
            return cached

        user_data = (
            get_user_model()
            .objects.filter(id=user_id, is_active=True)
            .values("company_id", "is_platform_admin")
            .first()
        )
        if not user_data:
            return None

        cache_timeout = getattr(settings, "TENANT_CACHE_TIMEOUT", 300)
        cache.set(cache_key, user_data, timeout=cache_timeout)
        return user_data
