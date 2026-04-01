from fastapi import Depends, HTTPException, status

from app.core.auth import AuthContext, get_auth_context
from app.core.config import settings


def require_permissions(*required: str):
    async def dependency(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
        if not required:
            return auth

        missing = [code for code in required if code not in auth.permissions]
        if missing:
            if auth.is_internal_service:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permissions for service token: {', '.join(missing)}",
                )
            if not auth.permissions and not settings.authz_strict:
                return auth
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permissions: {', '.join(missing)}",
            )
        return auth

    return dependency
