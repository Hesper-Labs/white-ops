"""Triggers & Automation API - manage event-driven triggers and their execution history."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_operator
from app.db.session import get_db
from app.models.trigger import Trigger, TriggerExecution
from app.models.user import User
from app.services.audit import log_action
from app.services.trigger_engine import trigger_engine

logger = structlog.get_logger()
router = APIRouter()


@router.get("/")
async def list_triggers(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    trigger_type: str | None = None,
    is_active: bool | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List all triggers with optional filters."""
    query = select(Trigger).where(Trigger.is_deleted.is_(False))

    if trigger_type:
        query = query.where(Trigger.trigger_type == trigger_type)
    if is_active is not None:
        query = query.where(Trigger.is_active == is_active)

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    query = query.order_by(Trigger.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    triggers = result.scalars().all()

    items = [
        {
            "id": str(t.id),
            "name": t.name,
            "trigger_type": t.trigger_type,
            "action_type": t.action_type,
            "is_active": t.is_active,
            "fire_count": t.fire_count,
            "last_fired_at": t.last_fired_at.isoformat() if t.last_fired_at else None,
            "config": t.config,
            "action_config": t.action_config,
            "created_at": t.created_at.isoformat(),
        }
        for t in triggers
    ]

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_trigger(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Create a new trigger."""
    name = data.get("name")
    trigger_type = data.get("trigger_type")
    action_type = data.get("action_type")

    if not name or not trigger_type or not action_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'name', 'trigger_type', and 'action_type' are required",
        )

    trigger = await trigger_engine.create_trigger(
        db=db,
        name=name,
        trigger_type=trigger_type,
        config=data.get("config", {}),
        action_type=action_type,
        action_config=data.get("action_config", {}),
        created_by=user.id,
    )

    return {
        "id": str(trigger.id),
        "name": trigger.name,
        "trigger_type": trigger.trigger_type,
        "action_type": trigger.action_type,
        "is_active": trigger.is_active,
        "created_at": trigger.created_at.isoformat(),
    }


@router.get("/{trigger_id}")
async def get_trigger(
    trigger_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Get trigger detail with execution stats."""
    result = await db.execute(
        select(Trigger).where(Trigger.id == trigger_id, Trigger.is_deleted.is_(False))
    )
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")

    stats = await trigger_engine.get_trigger_stats(db, trigger_id)

    return {
        "id": str(trigger.id),
        "name": trigger.name,
        "trigger_type": trigger.trigger_type,
        "config": trigger.config,
        "action_type": trigger.action_type,
        "action_config": trigger.action_config,
        "is_active": trigger.is_active,
        "fire_count": trigger.fire_count,
        "last_fired_at": trigger.last_fired_at.isoformat() if trigger.last_fired_at else None,
        "created_by": str(trigger.created_by) if trigger.created_by else None,
        "created_at": trigger.created_at.isoformat(),
        "updated_at": trigger.updated_at.isoformat(),
        "stats": stats,
    }


@router.put("/{trigger_id}")
async def update_trigger(
    trigger_id: uuid.UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Update a trigger's configuration."""
    result = await db.execute(
        select(Trigger).where(Trigger.id == trigger_id, Trigger.is_deleted.is_(False))
    )
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")

    updatable = ["name", "trigger_type", "config", "action_type", "action_config"]
    for field in updatable:
        if field in data:
            setattr(trigger, field, data[field])

    await db.flush()

    await log_action(
        db,
        action="trigger_updated",
        resource_type="trigger",
        resource_id=trigger_id,
        actor_type="user",
        actor_id=user.id,
        details=f"Trigger '{trigger.name}' updated",
    )
    logger.info("trigger_updated", trigger_id=str(trigger_id))

    return {
        "id": str(trigger.id),
        "name": trigger.name,
        "trigger_type": trigger.trigger_type,
        "action_type": trigger.action_type,
        "is_active": trigger.is_active,
        "updated_at": trigger.updated_at.isoformat(),
    }


@router.delete("/{trigger_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trigger(
    trigger_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> None:
    """Soft-delete a trigger."""
    result = await db.execute(
        select(Trigger).where(Trigger.id == trigger_id, Trigger.is_deleted.is_(False))
    )
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")

    trigger.soft_delete()
    await db.flush()

    await log_action(
        db,
        action="trigger_deleted",
        resource_type="trigger",
        resource_id=trigger_id,
        actor_type="user",
        actor_id=user.id,
        details=f"Trigger '{trigger.name}' deleted",
    )
    logger.info("trigger_deleted", trigger_id=str(trigger_id))


@router.post("/{trigger_id}/toggle")
async def toggle_trigger(
    trigger_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Enable or disable a trigger."""
    result = await db.execute(
        select(Trigger).where(Trigger.id == trigger_id, Trigger.is_deleted.is_(False))
    )
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")

    trigger.is_active = not trigger.is_active
    await db.flush()

    action = "enabled" if trigger.is_active else "disabled"
    await log_action(
        db,
        action=f"trigger_{action}",
        resource_type="trigger",
        resource_id=trigger_id,
        actor_type="user",
        actor_id=user.id,
        details=f"Trigger '{trigger.name}' {action}",
    )
    logger.info(f"trigger_{action}", trigger_id=str(trigger_id))

    return {
        "id": str(trigger.id),
        "name": trigger.name,
        "is_active": trigger.is_active,
        "message": f"Trigger {action}",
    }


@router.get("/{trigger_id}/history")
async def get_trigger_history(
    trigger_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Get execution history for a trigger."""
    # Verify trigger exists
    trigger_result = await db.execute(
        select(Trigger).where(Trigger.id == trigger_id, Trigger.is_deleted.is_(False))
    )
    if not trigger_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")

    count_result = await db.execute(
        select(func.count(TriggerExecution.id)).where(TriggerExecution.trigger_id == trigger_id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(TriggerExecution)
        .where(TriggerExecution.trigger_id == trigger_id)
        .order_by(TriggerExecution.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    executions = result.scalars().all()

    items = [
        {
            "id": str(e.id),
            "trigger_id": str(e.trigger_id),
            "status": e.status,
            "result": e.result,
            "error": e.error,
            "duration_ms": round(e.duration_ms, 2),
            "created_at": e.created_at.isoformat(),
        }
        for e in executions
    ]

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/{trigger_id}/test")
async def test_trigger(
    trigger_id: uuid.UUID,
    data: dict | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Test-fire a trigger with optional event data."""
    result = await db.execute(
        select(Trigger).where(Trigger.id == trigger_id, Trigger.is_deleted.is_(False))
    )
    trigger = result.scalar_one_or_none()
    if not trigger:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trigger not found")

    event_data = (data or {}).get("event_data", {"test": True, "triggered_by": str(user.id)})

    exec_result = await trigger_engine.execute_trigger(trigger_id, event_data, db)

    logger.info("trigger_tested", trigger_id=str(trigger_id), status=exec_result.get("status"))
    return exec_result
