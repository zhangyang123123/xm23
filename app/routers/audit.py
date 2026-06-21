from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.auth import require_admin
from app.services.audit_service import AuditService
from app.schemas.dtos import AuditLogOut, AuditLogDetail, AuditLogList

router = APIRouter(prefix="/admin/audit", tags=["审计日志"], dependencies=[Depends(require_admin)])


@router.get("", response_model=AuditLogList)
async def query_audit_logs(
    app_id: Optional[str] = None,
    api_key: Optional[str] = None,
    method: Optional[str] = Query(None, description="HTTP method e.g. GET, POST"),
    path: Optional[str] = None,
    status_code: Optional[int] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    svc = AuditService(db)
    items, total = await svc.query(
        app_id=app_id,
        api_key=api_key,
        method=method,
        path=path,
        status_code=status_code,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
    )
    return {"page": page, "page_size": page_size, "total": total, "items": items}


@router.get("/{log_id}", response_model=AuditLogDetail)
async def get_audit_log(log_id: int, db: AsyncSession = Depends(get_db)):
    svc = AuditService(db)
    log = await svc.get_by_id(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log


@router.get("/request/{request_id}", response_model=AuditLogDetail)
async def get_audit_log_by_request_id(request_id: str, db: AsyncSession = Depends(get_db)):
    svc = AuditService(db)
    log = await svc.get_by_request_id(request_id)
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    return log
