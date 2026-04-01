import hashlib
import os
import time
from dataclasses import dataclass
import logging

import httpx
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger("uvicorn.error")

_token_cache: dict[str, tuple[float, dict]] = {}


@dataclass
class AuthContext:
    user_id: str | None
    tenant_id: str | None
    role: str | None
    permissions: set[str]
    token: str
    is_internal_service: bool = False
    service_name: str | None = None


def _cache_get(cache_key: str) -> dict | None:
    item = _token_cache.get(cache_key)
    if not item:
        return None
    expires_at, data = item
    if expires_at < time.time():
        _token_cache.pop(cache_key, None)
        return None
    return data


def _cache_set(cache_key: str, data: dict, ttl: int) -> None:
    _token_cache[cache_key] = (time.time() + ttl, data)


def _extract_permissions(payload: dict) -> set[str]:
    perms = payload.get("permissions")
    if isinstance(perms, list):
        return {str(item) for item in perms}

    scope = payload.get("scope") or payload.get("scp")
    if isinstance(scope, str):
        return {part for part in scope.split(" ") if part}
    return set()


def _decode_user_token(token: str) -> dict:
    if not settings.auth_jwt_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="AI auth is not configured: AUTH_JWT_SECRET is missing.",
        )

    options = {"verify_aud": bool(settings.auth_jwt_audience)}
    try:
        return jwt.decode(
            token,
            settings.auth_jwt_secret,
            algorithms=[settings.auth_jwt_algorithm],
            audience=settings.auth_jwt_audience or None,
            issuer=settings.auth_jwt_issuer or None,
            options=options,
        )
    except jwt.PyJWTError as exc:
        raise ValueError(f"Invalid user access token: {exc}") from exc


def _decode_internal_token(token: str) -> dict:
    if not settings.auth_internal_token_secret:
        raise ValueError("AUTH_INTERNAL_TOKEN_SECRET is missing.")

    options = {"verify_aud": bool(settings.auth_internal_token_audience)}
    return jwt.decode(
        token,
        settings.auth_internal_token_secret,
        algorithms=[settings.auth_internal_token_algorithm],
        audience=settings.auth_internal_token_audience or None,
        issuer=settings.auth_internal_token_issuer or None,
        options=options,
    )


def _decode_token_with_context(token: str) -> tuple[dict, bool]:
    try:
        payload = _decode_internal_token(token)
        token_type = str(payload.get("token_type") or "").lower()
        if token_type == "service":
            return payload, True
    except Exception:
        pass

    try:
        payload = _decode_user_token(token)
        return payload, False
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid access token: {exc}",
        ) from exc


def _fetch_permissions_from_core(token: str) -> set[str]:
    if not settings.auth_permissions_from_core:
        return set()
    if not settings.core_auth_me_url:
        return set()

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    cache_key = f"perm:{token_hash}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return set(cached.get("permissions", []))

    started_at = time.perf_counter()
    try:
        with httpx.Client(timeout=settings.auth_core_timeout_seconds) as client:
            response = client.get(
                settings.core_auth_me_url,
                headers={"Authorization": f"Bearer {token}"},
            )
            response.raise_for_status()
            data = response.json()
        logger.info(
            "auth_permissions_core_fetch success ms=%.1f",
            (time.perf_counter() - started_at) * 1000,
        )
    except Exception as exc:
        logger.warning(
            "auth_permissions_core_fetch failed ms=%.1f error=%s",
            (time.perf_counter() - started_at) * 1000,
            str(exc),
        )
        if settings.authz_strict:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unable to validate permissions from core service: {exc}",
            ) from exc
        return set()

    permissions = data.get("permissions", [])
    if not isinstance(permissions, list):
        permissions = []
    normalized = {str(item) for item in permissions}
    _cache_set(cache_key, {"permissions": list(normalized)}, settings.auth_permissions_cache_seconds)
    return normalized


def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthContext:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Authorization header.")

    token = credentials.credentials
    payload, is_internal_service = _decode_token_with_context(token)

    service_name = None
    if is_internal_service:
        service_name = str(payload.get("service") or payload.get("sub") or "").strip() or None
        if settings.auth_internal_allowed_services and (not service_name or service_name not in settings.auth_internal_allowed_services):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Service is not allowed to access AI service.",
            )

    user_id = payload.get("user_id") or payload.get("user") or payload.get("sub")
    tenant_id = payload.get("company_id") or payload.get("tenant_id") or payload.get("tid")
    role = payload.get("role")
    permissions = _extract_permissions(payload)
    if not permissions and not is_internal_service:
        permissions = _fetch_permissions_from_core(token)

    # Optional backward-compatibility: allow role-derived defaults when permissions are not available.
    if not permissions and settings.auth_role_fallback_enabled and not is_internal_service:
        role_map = {
            "SUPER_ADMIN": {"ai.ingest", "ai.search", "ai.chat", "ai.dispatch", "ai.doc.update", "ai.doc.delete"},
            "COMPANY_ADMIN": {"ai.ingest", "ai.search", "ai.chat", "ai.dispatch", "ai.doc.update", "ai.doc.delete"},
        }
        permissions = role_map.get(str(role), set())

    return AuthContext(
        user_id=str(user_id) if user_id else None,
        tenant_id=str(tenant_id) if tenant_id else None,
        role=str(role) if role else None,
        permissions=permissions,
        token=token,
        is_internal_service=is_internal_service,
        service_name=service_name,
    )


def get_runtime_env_snapshot() -> dict[str, str]:
    keys = [
        "AUTH_JWT_ALGORITHM",
        "AUTH_JWT_ISSUER",
        "AUTH_JWT_AUDIENCE",
        "AUTH_INTERNAL_TOKEN_ISSUER",
        "AUTH_INTERNAL_TOKEN_AUDIENCE",
        "AUTH_INTERNAL_ALLOWED_SERVICES",
        "AUTH_PERMISSIONS_FROM_CORE",
        "AUTHZ_STRICT",
        "AUTH_ROLE_FALLBACK_ENABLED",
        "CORE_AUTH_ME_URL",
    ]
    return {key: os.getenv(key, "") for key in keys}
