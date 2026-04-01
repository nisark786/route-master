from fastapi import Depends, Header, HTTPException, status

from app.core.auth import AuthContext, get_auth_context


async def get_tenant_id(
    auth: AuthContext = Depends(get_auth_context),
    x_tenant_id: str | None = Header(default=None),
) -> str:
    token_tenant = auth.tenant_id.strip() if auth.tenant_id else None
    header_tenant = x_tenant_id.strip() if x_tenant_id else None

    if token_tenant and header_tenant and token_tenant != header_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant header does not match token tenant.",
        )

    tenant_id = token_tenant or header_tenant
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing tenant context. Provide token company_id or X-Tenant-Id.",
        )
    return tenant_id
