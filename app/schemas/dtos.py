from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict


class ApplicationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    owner: str = Field(..., min_length=1, max_length=64)


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = None
    owner: Optional[str] = None
    is_active: Optional[bool] = None


class ApplicationOut(ApplicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    app_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class Pagination(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int
    items: List[Any]


class ApplicationList(Pagination):
    items: List[ApplicationOut]


class CredentialCreate(BaseModel):
    name: Optional[str] = Field(None, max_length=128)
    expires_at: Optional[datetime] = None


class CredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    app_id: str
    api_key: str
    secret_fingerprint: str
    name: Optional[str]
    is_active: bool
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    created_at: datetime


class CredentialCreated(CredentialOut):
    api_secret: str


class CredentialList(Pagination):
    items: List[CredentialOut]


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: str
    app_id: Optional[str]
    api_key: Optional[str]
    method: str
    path: str
    route: Optional[str]
    status_code: int
    client_ip: Optional[str]
    user_agent: Optional[str]
    latency_ms: int
    error_message: Optional[str]
    created_at: datetime


class AuditLogDetail(AuditLogOut):
    query_params: Optional[str]
    request_body: Optional[str]
    response_body: Optional[str]


class AuditLogQuery(BaseModel):
    app_id: Optional[str] = None
    api_key: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    page: int = 1
    page_size: int = 20


class AuditLogList(Pagination):
    items: List[AuditLogOut]
