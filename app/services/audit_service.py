from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import AuditLog


class AuditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_log(
        self,
        request_id: str,
        method: str,
        path: str,
        status_code: int,
        latency_ms: int,
        app_id: Optional[str] = None,
        api_key: Optional[str] = None,
        route: Optional[str] = None,
        query_params: Optional[str] = None,
        request_body: Optional[str] = None,
        response_body: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> AuditLog:
        log = AuditLog(
            request_id=request_id,
            app_id=app_id,
            api_key=api_key,
            method=method,
            path=path,
            route=route,
            query_params=query_params,
            request_body=request_body,
            status_code=status_code,
            response_body=response_body,
            client_ip=client_ip,
            user_agent=user_agent,
            latency_ms=latency_ms,
            error_message=error_message,
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)
        return log

    async def query(
        self,
        app_id: Optional[str] = None,
        api_key: Optional[str] = None,
        method: Optional[str] = None,
        path: Optional[str] = None,
        status_code: Optional[int] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[list, int]:
        conditions = []
        if app_id:
            conditions.append(AuditLog.app_id == app_id)
        if api_key:
            conditions.append(AuditLog.api_key == api_key)
        if method:
            conditions.append(AuditLog.method == method.upper())
        if path:
            conditions.append(AuditLog.path.ilike(f"%{path}%"))
        if status_code is not None:
            conditions.append(AuditLog.status_code == status_code)
        if start_time:
            conditions.append(AuditLog.created_at >= start_time)
        if end_time:
            conditions.append(AuditLog.created_at <= end_time)

        where_clause = and_(*conditions) if conditions else None

        count_query = select(func.count(AuditLog.id))
        if where_clause is not None:
            count_query = count_query.where(where_clause)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = select(AuditLog)
        if where_clause is not None:
            query = query.where(where_clause)
        query = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = list(result.scalars().all())
        return items, total

    async def get_by_id(self, log_id: int) -> Optional[AuditLog]:
        result = await self.db.execute(select(AuditLog).where(AuditLog.id == log_id))
        return result.scalar_one_or_none()

    async def get_by_request_id(self, request_id: str) -> Optional[AuditLog]:
        result = await self.db.execute(select(AuditLog).where(AuditLog.request_id == request_id))
        return result.scalar_one_or_none()
