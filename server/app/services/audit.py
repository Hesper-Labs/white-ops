"""Audit logging service - tracks all important actions."""

import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog

logger = structlog.get_logger()


async def log_action(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: uuid.UUID | str | None = None,
    actor_type: str = "user",
    actor_id: uuid.UUID | str | None = None,
    details: str | None = None,
    changes: dict | None = None,
    ip_address: str | None = None,
) -> None:
    """Record an audit log entry."""
    entry = AuditLog(
        action=action,
        resource_type=resource_type,
        resource_id=uuid.UUID(str(resource_id)) if resource_id else None,
        actor_type=actor_type,
        actor_id=uuid.UUID(str(actor_id)) if actor_id else None,
        details=details,
        changes=changes or {},
        ip_address=ip_address,
    )
    db.add(entry)

    logger.info(
        "audit_log",
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        actor_type=actor_type,
        actor_id=str(actor_id) if actor_id else None,
    )
