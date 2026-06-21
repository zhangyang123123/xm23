from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.auth import require_admin
from app.services.app_service import ApplicationService, CredentialService
from app.schemas.dtos import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationOut,
    ApplicationList,
    CredentialCreate,
    CredentialOut,
    CredentialCreated,
    CredentialList,
)

router = APIRouter(prefix="/admin/applications", tags=["应用管理"], dependencies=[Depends(require_admin)])


@router.post("", response_model=ApplicationOut, status_code=status.HTTP_201_CREATED)
async def create_application(data: ApplicationCreate, db: AsyncSession = Depends(get_db)):
    svc = ApplicationService(db)
    return await svc.create(name=data.name, owner=data.owner, description=data.description)


@router.get("", response_model=ApplicationList)
async def list_applications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    svc = ApplicationService(db)
    items, total = await svc.list(page=page, page_size=page_size, keyword=keyword)
    return {"page": page, "page_size": page_size, "total": total, "items": items}


@router.get("/{app_id}", response_model=ApplicationOut)
async def get_application(app_id: str, db: AsyncSession = Depends(get_db)):
    svc = ApplicationService(db)
    app = await svc.get_by_app_id(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.patch("/{app_id}", response_model=ApplicationOut)
async def update_application(app_id: str, data: ApplicationUpdate, db: AsyncSession = Depends(get_db)):
    svc = ApplicationService(db)
    app = await svc.update(app_id, **data.model_dump(exclude_unset=True))
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.delete("/{app_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_application(app_id: str, db: AsyncSession = Depends(get_db)):
    svc = ApplicationService(db)
    ok = await svc.delete(app_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Application not found")
    return None


@router.post("/{app_id}/credentials", response_model=CredentialCreated, status_code=status.HTTP_201_CREATED)
async def create_credential(app_id: str, data: CredentialCreate, db: AsyncSession = Depends(get_db)):
    app_svc = ApplicationService(db)
    app = await app_svc.get_by_app_id(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    cred_svc = CredentialService(db)
    cred, secret = await cred_svc.create(app_id=app_id, name=data.name, expires_at=data.expires_at)
    return {
        **CredentialOut.model_validate(cred).model_dump(),
        "api_secret": secret,
    }


@router.get("/{app_id}/credentials", response_model=CredentialList)
async def list_credentials(
    app_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    app_svc = ApplicationService(db)
    app = await app_svc.get_by_app_id(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    cred_svc = CredentialService(db)
    items, total = await cred_svc.list_by_app(app_id=app_id, page=page, page_size=page_size)
    return {"page": page, "page_size": page_size, "total": total, "items": items}


@router.post("/{app_id}/credentials/{credential_id}/disable", response_model=CredentialOut)
async def disable_credential(app_id: str, credential_id: int, db: AsyncSession = Depends(get_db)):
    app_svc = ApplicationService(db)
    app = await app_svc.get_by_app_id(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    cred_svc = CredentialService(db)
    cred = await cred_svc.get_by_id(credential_id)
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    if cred.app_id != app_id:
        raise HTTPException(status_code=400, detail="Credential does not belong to this application")
    cred = await cred_svc.set_active(credential_id, is_active=False)
    return cred


@router.post("/{app_id}/credentials/{credential_id}/enable", response_model=CredentialOut)
async def enable_credential(app_id: str, credential_id: int, db: AsyncSession = Depends(get_db)):
    app_svc = ApplicationService(db)
    app = await app_svc.get_by_app_id(app_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    cred_svc = CredentialService(db)
    cred = await cred_svc.get_by_id(credential_id)
    if not cred:
        raise HTTPException(status_code=404, detail="Credential not found")
    if cred.app_id != app_id:
        raise HTTPException(status_code=400, detail="Credential does not belong to this application")
    cred = await cred_svc.set_active(credential_id, is_active=True)
    return cred
