from typing import Optional
from datetime import datetime, timezone
from fastapi import Request, Header, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.app_service import CredentialService
from app.core.security import verify_secret
from app.config import settings
from app.models.entities import ApiCredential

security = HTTPBearer(auto_error=False)


class AuthContext:
    def __init__(self, credential: ApiCredential):
        self.credential = credential
        self.app_id = credential.app_id
        self.api_key = credential.api_key


async def require_admin(
    authorization: Optional[str] = Header(None),
) -> None:
    token = None
    if authorization:
        if authorization.lower().startswith("bearer "):
            token = authorization[7:]
        else:
            token = authorization
    if not token or token != settings.ADMIN_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def authenticate_api(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_api_key: Optional[str] = Header(None),
    x_api_secret: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> AuthContext:
    api_key = x_api_key
    api_secret = x_api_secret

    if not api_key and credentials:
        api_key = credentials.credentials
        api_secret = None
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key (use X-API-Key header or Authorization: Bearer)",
        )

    svc = CredentialService(db)
    cred = await svc.get_by_api_key(api_key)
    if not cred:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )

    if not cred.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Credential has been disabled",
        )

    if cred.expires_at and cred.expires_at.replace(tzinfo=None) < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Credential has expired",
        )

    if api_secret and not verify_secret(api_secret, cred.secret_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Secret",
        )

    await svc.touch_last_used(cred.id)
    ctx = AuthContext(cred)
    request.state.auth_context = ctx
    return ctx
