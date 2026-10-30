"""SQLAlchemy 2.x async models for PostgreSQL 16.

Indexes required by the task are declared explicitly. This module needs
SQLAlchemy installed; it is NOT imported by the pure-stdlib test suite.
"""
from __future__ import annotations

from sqlalchemy import (JSON, BigInteger, Boolean, Date, DateTime, ForeignKey,
                        Index, Integer, String, Text, UniqueConstraint, func)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(64))
    display_name: Mapped[str | None] = mapped_column(String(128))
    language: Mapped[str] = mapped_column(String(8), default="id")
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Jakarta")
    plan: Mapped[str] = mapped_column(String(32), default="free")
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Subscription(Base):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    plan: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str | None] = mapped_column(String(64))
    provider_customer_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="active")
    period_start: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[object | None] = mapped_column(DateTime(timezone=True))


class UsageDaily(Base):
    __tablename__ = "usage_daily"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    date: Mapped[object] = mapped_column(Date)
    operation: Mapped[str] = mapped_column(String(64))
    requests: Mapped[int] = mapped_column(Integer, default=0)
    credits_estimated: Mapped[int] = mapped_column(Integer, default=0)
    bytes: Mapped[int] = mapped_column(BigInteger, default=0)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (Index("ix_usage_daily_user_date", "user_id", "date"),
                      UniqueConstraint("user_id", "date", "operation"))


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="queued")
    input_hash: Mapped[str | None] = mapped_column(String(64))
    context_job_id: Mapped[str | None] = mapped_column(String(128), index=True)
    progress: Mapped[int] = mapped_column(Integer, default=0)
    request_id: Mapped[str | None] = mapped_column(String(128), index=True)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message_safe: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (Index("ix_jobs_status_created", "status", "created_at"),
                      Index("ix_jobs_user_created", "user_id", "created_at"))


class JobResult(Base):
    __tablename__ = "job_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"), unique=True)
    result_type: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[dict | None] = mapped_column(JSON)
    storage_url: Mapped[str | None] = mapped_column(String(512))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))


class SavedItem(Base):
    __tablename__ = "saved_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(64))
    title: Mapped[str | None] = mapped_column(String(256))
    url: Mapped[str | None] = mapped_column(String(2048))
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Monitor(Base):
    __tablename__ = "monitors"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    context_monitor_id: Mapped[str | None] = mapped_column(String(128), index=True)
    target: Mapped[str] = mapped_column(String(2048))
    type: Mapped[str] = mapped_column(String(64), default="page")
    status: Mapped[str] = mapped_column(String(32), default="active")
    config_json: Mapped[dict | None] = mapped_column(JSON)
    last_event_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(64))
    event_id: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    payload_hash: Mapped[str] = mapped_column(String(64))
    received_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    processed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True))


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(BigInteger, index=True)
    action: Mapped[str] = mapped_column(String(128))
    target_type: Mapped[str | None] = mapped_column(String(64))
    target_id: Mapped[str | None] = mapped_column(String(128))
    metadata_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdminSetting(Base):
    """Admin settings, e.g. the Fernet-encrypted Context.dev API key set
    from the /admin panel. The value column holds ONLY ciphertext, never
    a plaintext key (see services/admin_key_service.py)."""
    __tablename__ = "admin_settings"
    id: Mapped[int] = mapped_column(primary_key=True)
    key_name: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    encrypted_value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_by: Mapped[int | None] = mapped_column(BigInteger)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AdminBroadcast(Base):
    __tablename__ = "admin_broadcasts"
    id: Mapped[int] = mapped_column(primary_key=True)
    admin_id: Mapped[int] = mapped_column(BigInteger)
    message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="draft")
    counters: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
