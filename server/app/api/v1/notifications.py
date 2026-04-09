"""Notification System API - manage notifications, channels, and routing rules."""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_admin
from app.db.session import get_db
from app.models.notification import Notification, NotificationRule
from app.models.user import User
from app.services.notification_service import notification_service

logger = structlog.get_logger()
router = APIRouter()


# ---------------------------------------------------------------------------
# Notification list and management
# ---------------------------------------------------------------------------

@router.get("/")
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    unread: bool | None = None,
    severity: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List notifications for the current user."""
    conditions = [
        Notification.user_id == user.id,
        Notification.is_deleted.is_(False),
    ]
    if unread is True:
        conditions.append(Notification.is_read.is_(False))
    elif unread is False:
        conditions.append(Notification.is_read.is_(True))
    if severity:
        conditions.append(Notification.severity == severity)

    count_result = await db.execute(
        select(func.count(Notification.id)).where(and_(*conditions))
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Notification)
        .where(and_(*conditions))
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    notifications = result.scalars().all()

    items = [
        {
            "id": str(n.id),
            "channel": n.channel,
            "subject": n.subject,
            "body": n.body,
            "severity": n.severity,
            "is_read": n.is_read,
            "read_at": n.read_at.isoformat() if n.read_at else None,
            "metadata": n.metadata_,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/unread-count")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Get the count of unread notifications."""
    count = await notification_service.get_unread_count(user.id, db)
    return {"unread_count": count}


@router.put("/{notification_id}/read")
async def mark_as_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Mark a notification as read."""
    # Verify ownership
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user.id,
            Notification.is_deleted.is_(False),
        )
    )
    notification = result.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    marked = await notification_service.mark_read(notification_id, db)
    if not marked:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    return {"id": str(notification_id), "is_read": True}


@router.put("/read-all")
async def mark_all_as_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Mark all notifications as read for the current user."""
    result = await db.execute(
        select(Notification).where(
            Notification.user_id == user.id,
            Notification.is_read.is_(False),
            Notification.is_deleted.is_(False),
        )
    )
    notifications = list(result.scalars().all())

    now = datetime.now(timezone.utc)
    count = 0
    for n in notifications:
        n.is_read = True
        n.read_at = now
        count += 1

    await db.flush()

    logger.info("notifications_mark_all_read", user_id=str(user.id), count=count)
    return {"marked_count": count}


# ---------------------------------------------------------------------------
# Notification channels
# ---------------------------------------------------------------------------

# In-memory store for channels (in production, use a DB model)
_channels: dict[str, dict] = {}


@router.get("/channels")
async def list_channels(
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List notification channels."""
    items = list(_channels.values())
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    total = len(items)
    paged = items[skip : skip + limit]
    return {"items": paged, "total": total, "skip": skip, "limit": limit}


@router.post("/channels", status_code=status.HTTP_201_CREATED)
async def add_channel(
    data: dict,
    user: User = Depends(require_admin),
) -> dict:
    """Add a notification channel."""
    channel_id = str(uuid.uuid4())
    channel = {
        "id": channel_id,
        "name": data.get("name", ""),
        "type": data.get("type", "webhook"),  # email, slack, webhook, telegram
        "config": data.get("config", {}),
        "is_active": True,
        "created_by": str(user.id),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _channels[channel_id] = channel
    logger.info("notification_channel_added", channel_id=channel_id, type=channel["type"])
    return channel


@router.put("/channels/{channel_id}")
async def update_channel(
    channel_id: str,
    data: dict,
    user: User = Depends(require_admin),
) -> dict:
    """Update a notification channel."""
    channel = _channels.get(channel_id)
    if not channel:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Channel not found")

    updatable = ["name", "type", "config", "is_active"]
    for field in updatable:
        if field in data:
            channel[field] = data[field]

    channel["updated_at"] = datetime.now(timezone.utc).isoformat()
    logger.info("notification_channel_updated", channel_id=channel_id)
    return channel


# ---------------------------------------------------------------------------
# Notification routing rules
# ---------------------------------------------------------------------------

@router.get("/rules")
async def list_notification_rules(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List notification routing rules."""
    count_result = await db.execute(
        select(func.count(NotificationRule.id)).where(NotificationRule.is_deleted.is_(False))
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(NotificationRule)
        .where(NotificationRule.is_deleted.is_(False))
        .order_by(NotificationRule.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rules = result.scalars().all()

    items = [
        {
            "id": str(r.id),
            "name": r.name,
            "event_type": r.event_type,
            "conditions": r.conditions,
            "channel": r.channel,
            "template": r.template,
            "is_active": r.is_active,
            "config": r.config,
            "created_at": r.created_at.isoformat(),
        }
        for r in rules
    ]

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/rules", status_code=status.HTTP_201_CREATED)
async def create_notification_rule(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Create a notification routing rule."""
    name = data.get("name")
    event_type = data.get("event_type")
    channel = data.get("channel")

    if not name or not event_type or not channel:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'name', 'event_type', and 'channel' are required",
        )

    rule = NotificationRule(
        name=name,
        event_type=event_type,
        conditions=data.get("conditions", {}),
        channel=channel,
        template=data.get("template"),
        is_active=data.get("is_active", True),
        config=data.get("config", {}),
    )
    db.add(rule)
    await db.flush()

    logger.info("notification_rule_created", rule_id=str(rule.id), event_type=event_type)

    return {
        "id": str(rule.id),
        "name": rule.name,
        "event_type": rule.event_type,
        "channel": rule.channel,
        "is_active": rule.is_active,
        "created_at": rule.created_at.isoformat(),
    }
