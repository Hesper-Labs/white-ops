import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_operator
from app.db.session import get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter()


@router.get("/", response_model=list[TaskResponse])
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    status_filter: str | None = None,
    priority: str | None = None,
    agent_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[Task]:
    query = select(Task)
    if status_filter:
        query = query.where(Task.status == status_filter)
    if priority:
        query = query.where(Task.priority == priority)
    if agent_id:
        query = query.where(Task.agent_id == uuid.UUID(agent_id))
    result = await db.execute(
        query.order_by(Task.created_at.desc()).limit(limit).offset(offset)
    )
    return list(result.scalars().all())


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> Task:
    task = Task(
        title=data.title,
        description=data.description,
        instructions=data.instructions,
        priority=data.priority,
        required_tools=data.required_tools,
        max_retries=data.max_retries,
        assigned_by=user.id,
    )
    if data.agent_id:
        task.agent_id = uuid.UUID(data.agent_id)
        task.status = "assigned"
    if data.deadline:
        task.deadline = datetime.fromisoformat(data.deadline)
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


@router.get("/stats")
async def task_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    total = await db.execute(select(func.count(Task.id)))
    by_status = await db.execute(
        select(Task.status, func.count(Task.id)).group_by(Task.status)
    )
    by_priority = await db.execute(
        select(Task.priority, func.count(Task.id)).group_by(Task.priority)
    )
    return {
        "total": total.scalar() or 0,
        "by_status": dict(by_status.all()),
        "by_priority": dict(by_priority.all()),
    }


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Task:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> Task:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    update_data = data.model_dump(exclude_unset=True)
    if "agent_id" in update_data and update_data["agent_id"]:
        update_data["agent_id"] = uuid.UUID(update_data["agent_id"])
    for field, value in update_data.items():
        setattr(task, field, value)

    await db.flush()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> None:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    await db.delete(task)


@router.post("/{task_id}/cancel", response_model=TaskResponse)
async def cancel_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> Task:
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    if task.status in ("completed", "cancelled"):
        raise HTTPException(status_code=400, detail=f"Cannot cancel task in {task.status} state")
    task.status = "cancelled"
    task.completed_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(task)
    return task
