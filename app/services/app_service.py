import secrets
from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Application, ApiCredential
from app.core.security import hash_secret, generate_api_key, generate_api_secret, fingerprint_secret


def _gen_app_id() -> str:
    return f"app_{secrets.token_urlsafe(16)}"


class ApplicationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, name: str, owner: str, description: Optional[str] = None) -> Application:
        app = Application(
            app_id=_gen_app_id(),
            name=name,
            owner=owner,
            description=description,
        )
        self.db.add(app)
        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def get_by_app_id(self, app_id: str) -> Optional[Application]:
        result = await self.db.execute(select(Application).where(Application.app_id == app_id))
        return result.scalar_one_or_none()

    async def list(self, page: int = 1, page_size: int = 20, keyword: Optional[str] = None) -> Tuple[list, int]:
        query = select(Application)
        count_query = select(func.count(Application.id))

        if keyword:
            pattern = f"%{keyword}%"
            query = query.where(or_(Application.name.ilike(pattern), Application.owner.ilike(pattern)))
            count_query = count_query.where(or_(Application.name.ilike(pattern), Application.owner.ilike(pattern)))

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(Application.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def update(self, app_id: str, **kwargs) -> Optional[Application]:
        app = await self.get_by_app_id(app_id)
        if not app:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(app, key):
                setattr(app, key, value)
        await self.db.commit()
        await self.db.refresh(app)
        return app

    async def delete(self, app_id: str) -> bool:
        app = await self.get_by_app_id(app_id)
        if not app:
            return False
        await self.db.delete(app)
        await self.db.commit()
        return True


class CredentialService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, app_id: str, name: Optional[str] = None, expires_at: Optional[datetime] = None) -> Tuple[ApiCredential, str]:
        api_key = generate_api_key()
        api_secret = generate_api_secret()
        secret_hash = hash_secret(api_secret)
        fingerprint = fingerprint_secret(api_secret)

        cred = ApiCredential(
            app_id=app_id,
            api_key=api_key,
            secret_hash=secret_hash,
            secret_fingerprint=fingerprint,
            name=name,
            expires_at=expires_at,
        )
        self.db.add(cred)
        await self.db.commit()
        await self.db.refresh(cred)
        return cred, api_secret

    async def get_by_api_key(self, api_key: str) -> Optional[ApiCredential]:
        result = await self.db.execute(
            select(ApiCredential).where(ApiCredential.api_key == api_key)
        )
        return result.scalar_one_or_none()

    async def list_by_app(self, app_id: str, page: int = 1, page_size: int = 20) -> Tuple[list, int]:
        count_query = select(func.count(ApiCredential.id)).where(ApiCredential.app_id == app_id)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = (
            select(ApiCredential)
            .where(ApiCredential.app_id == app_id)
            .order_by(ApiCredential.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def set_active(self, credential_id: int, is_active: bool) -> Optional[ApiCredential]:
        result = await self.db.execute(select(ApiCredential).where(ApiCredential.id == credential_id))
        cred = result.scalar_one_or_none()
        if not cred:
            return None
        cred.is_active = is_active
        await self.db.commit()
        await self.db.refresh(cred)
        return cred

    async def touch_last_used(self, credential_id: int) -> None:
        result = await self.db.execute(select(ApiCredential).where(ApiCredential.id == credential_id))
        cred = result.scalar_one_or_none()
        if cred:
            cred.last_used_at = datetime.utcnow()
            await self.db.commit()
