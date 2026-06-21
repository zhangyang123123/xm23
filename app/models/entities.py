from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.database import Base


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    owner = Column(String(64), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    credentials = relationship("ApiCredential", back_populates="application", cascade="all, delete-orphan")


class ApiCredential(Base):
    __tablename__ = "api_credentials"

    id = Column(Integer, primary_key=True, index=True)
    app_id = Column(String(64), ForeignKey("applications.app_id", ondelete="CASCADE"), nullable=False)
    api_key = Column(String(128), unique=True, index=True, nullable=False)
    secret_hash = Column(String(255), nullable=False)
    secret_fingerprint = Column(String(32), nullable=False)
    name = Column(String(128), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    application = relationship("Application", back_populates="credentials")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(64), unique=True, index=True, nullable=False)
    app_id = Column(String(64), index=True, nullable=True)
    api_key = Column(String(128), index=True, nullable=True)
    method = Column(String(16), nullable=False)
    path = Column(String(1024), nullable=False)
    route = Column(String(512), nullable=True)
    query_params = Column(Text, nullable=True)
    request_body = Column(Text, nullable=True)
    status_code = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=True)
    client_ip = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    latency_ms = Column(Integer, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_audit_app_time", "app_id", "created_at"),
        Index("ix_audit_path_time", "path", "created_at"),
        Index("ix_audit_created_at", "created_at"),
    )
