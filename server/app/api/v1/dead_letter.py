"""Dead Letter Queue API - manage failed tasks for retry or discard."""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_admin, require_operator
from app.db.session import get_db
from app.models.task import Task
from app.models.user import User
from app.services.audit import log_action

logger = structlog.get_logger()
router = APIRouter()


@router.get("/")
async def list_dead_letter(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    error_type: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List failed tasks in the dead letter queue."""
    query = select(Task).where(
        Task.status == "failed",
        Task.retry_count >= Task.max_retries,
        Task.is_deleted.is_(False),
    )

    if error_type:
        query = query.where(Task.error.ilike(f"%{error_type}%"))

    # Get total count
    count_query = select(func.count()).select_from(
        query.subquery()
    )
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get paginated results
    query = query.order_by(Task.updated_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    tasks = result.scalars().all()

    items = [
        {
            "id": str(t.id),
            "title": t.title,
            "status": t.status,
            "error": t.error,
            "retry_count": t.retry_count,
            "max_retries": t.max_retries,
            "agent_id": str(t.agent_id) if t.agent_id else None,
            "priority": t.priority,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
            "metadata": t.metadata_,
        }
        for t in tasks
    ]

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.get("/stats")
async def get_dlq_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Get dead letter queue statistics."""
    base_filter = [
        Task.status == "failed",
        Task.retry_count >= Task.max_retries,
        Task.is_deleted.is_(False),
    ]

    # Total count
    total_result = await db.execute(
        select(func.count(Task.id)).where(*base_filter)
    )
    total = total_result.scalar() or 0

    # Count by priority
    priority_result = await db.execute(
        select(Task.priority, func.count(Task.id))
        .where(*base_filter)
        .group_by(Task.priority)
    )
    by_priority = dict(priority_result.all())

    # Oldest entry
    oldest_result = await db.execute(
        select(func.min(Task.created_at)).where(*base_filter)
    )
    oldest = oldest_result.scalar()

    # Retryable count (tasks that could potentially be retried)
    retryable_result = await db.execute(
        select(func.count(Task.id)).where(
            *base_filter,
            Task.error.isnot(None),
        )
    )
    retryable = retryable_result.scalar() or 0

    return {
        "total": total,
        "retryable": retryable,
        "by_priority": by_priority,
        "oldest_entry": oldest.isoformat() if oldest else None,
    }


@router.get("/{task_id}")
async def get_dlq_entry(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Get detailed information about a DLQ entry."""
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.status == "failed",
            Task.is_deleted.is_(False),
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DLQ entry not found")

    return {
        "id": str(task.id),
        "title": task.title,
        "description": task.description,
        "instructions": task.instructions,
        "status": task.status,
        "error": task.error,
        "result": task.result,
        "retry_count": task.retry_count,
        "max_retries": task.max_retries,
        "agent_id": str(task.agent_id) if task.agent_id else None,
        "priority": task.priority,
        "metadata": task.metadata_,
        "output_files": task.output_files,
        "created_at": task.created_at.isoformat(),
        "updated_at": task.updated_at.isoformat(),
        "started_at": task.started_at.isoformat() if task.started_at else None,
        "completed_at": task.completed_at.isoformat() if task.completed_at else None,
    }


@router.post("/{task_id}/retry")
async def retry_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Retry a failed task from the DLQ."""
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.status == "failed",
            Task.is_deleted.is_(False),
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DLQ entry not found")

    # Reset task for retry
    task.status = "pending"
    task.error = None
    task.retry_count = 0
    task.started_at = None
    task.completed_at = None
    task.result = None
    await db.flush()

    await log_action(
        db,
        action="dlq_task_retried",
        resource_type="task",
        resource_id=task_id,
        actor_type="user",
        actor_id=user.id,
        details=f"Task '{task.title}' retried from DLQ",
    )
    logger.info("dlq_task_retried", task_id=str(task_id), user_id=str(user.id))

    return {
        "id": str(task.id),
        "title": task.title,
        "status": task.status,
        "message": "Task has been re-queued for retry",
    }


@router.post("/retry-all")
async def retry_all(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Retry all eligible failed tasks in the DLQ."""
    result = await db.execute(
        select(Task).where(
            Task.status == "failed",
            Task.retry_count >= Task.max_retries,
            Task.is_deleted.is_(False),
        )
    )
    tasks = list(result.scalars().all())

    retried = 0
    for task in tasks:
        task.status = "pending"
        task.error = None
        task.retry_count = 0
        task.started_at = None
        task.completed_at = None
        task.result = None
        retried += 1

    await db.flush()

    await log_action(
        db,
        action="dlq_retry_all",
        resource_type="task",
        actor_type="user",
        actor_id=user.id,
        details=f"Retried {retried} tasks from DLQ",
    )
    logger.info("dlq_retry_all", count=retried, user_id=str(user.id))

    return {"retried_count": retried, "message": f"{retried} tasks re-queued for retry"}


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def discard_dlq_entry(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> None:
    """Discard a task from the DLQ (soft-delete)."""
    result = await db.execute(
        select(Task).where(
            Task.id == task_id,
            Task.status == "failed",
            Task.is_deleted.is_(False),
        )
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="DLQ entry not found")

    task.soft_delete()
    await db.flush()

    await log_action(
        db,
        action="dlq_task_discarded",
        resource_type="task",
        resource_id=task_id,
        actor_type="user",
        actor_id=user.id,
        details=f"Task '{task.title}' discarded from DLQ",
    )
    logger.info("dlq_task_discarded", task_id=str(task_id))


@router.delete("/", status_code=status.HTTP_200_OK)
async def purge_dlq(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Purge all entries from the DLQ (soft-delete)."""
    result = await db.execute(
        select(Task).where(
            Task.status == "failed",
            Task.retry_count >= Task.max_retries,
            Task.is_deleted.is_(False),
        )
    )
    tasks = list(result.scalars().all())

    purged = 0
    for task in tasks:
        task.soft_delete()
        purged += 1

    await db.flush()

    await log_action(
        db,
        action="dlq_purged",
        resource_type="task",
        actor_type="user",
        actor_id=user.id,
        details=f"Purged {purged} tasks from DLQ",
    )
    logger.info("dlq_purged", count=purged, user_id=str(user.id))

    return {"purged_count": purged, "message": f"{purged} tasks purged from DLQ"}
