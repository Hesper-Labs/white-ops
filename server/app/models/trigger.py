"""Trigger models for the trigger engine."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Trigger(Base):
    __tablename__ = "triggers"

    name: Mapped[str] = mapped_column(String(255))
    trigger_type: Mapped[str] = mapped_column(String(50), index=True)  # event, cron, webhook, threshold
    config: Mapped[dict] = mapped_column(JSONB, default=dict)  # type-specific config
    action_type: Mapped[str] = mapped_column(String(50))  # create_task, send_notification, execute_workflow, call_webhook
    action_config: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    last_fired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fire_count: Mapped[int] = mapped_column(Integer, default=0)


class TriggerExecution(Base):
    __tablename__ = "trigger_executions"

    trigger_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("triggers.id"), index=True
    )
    status: Mapped[str] = mapped_column(String(50))  # success, failure, skipped
    result: Mapped[dict] = mapped_column(JSONB, default=dict)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[float] = mapped_column(Float, default=0.0)
    event_data: Mapped[dict] = mapped_column(JSONB, default=dict)
