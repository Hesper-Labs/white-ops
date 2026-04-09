"""Scheduled tasks API - cron-based recurring task execution."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import Boolean, String, Text, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.auth import require_operator
from app.db.session import get_db
from app.models.base import Base
from app.models.user import User

router = APIRouter()


# Model
class Schedule(Base):
    __tablename__ = "schedules"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cron_expression: Mapped[str] = mapped_column(String(50))
    agent_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    task_template: Mapped[dict] = mapped_column(JSONB, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[str | None] = mapped_column(String(50), nullable=True)
    next_run_at: Mapped[str | None] = mapped_column(String(50), nullable=True)


# Schemas
class ScheduleCreate(BaseModel):
    name: str
    description: str | None = None
    cron_expression: str
    agent_id: str | None = None
    task_template: dict = {}


class ScheduleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    cron_expression: str | None = None
    agent_id: str | None = None
    is_enabled: bool | None = None


@router.get("/")
async def list_schedules(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> list[dict]:
    result = await db.execute(select(Schedule).order_by(Schedule.created_at.desc()))
    items = result.scalars().all()
    return [
        {
            "id": str(s.id),
            "name": s.name,
            "description": s.description,
            "cron_expression": s.cron_expression,
            "agent_id": s.agent_id,
            "is_enabled": s.is_enabled,
            "last_run_at": s.last_run_at,
            "next_run_at": s.next_run_at,
            "created_at": str(s.created_at),
        }
        for s in items
    ]


@router.post("/", status_code=201)
async def create_schedule(
    data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    schedule = Schedule(
        name=data.name,
        description=data.description,
        cron_expression=data.cron_expression,
        agent_id=data.agent_id,
        task_template=data.task_template,
    )
    db.add(schedule)
    await db.flush()
    await db.refresh(schedule)
    return {"id": str(schedule.id), "name": schedule.name}


@router.patch("/{schedule_id}")
async def update_schedule(
    schedule_id: uuid.UUID,
    data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)

    await db.flush()
    return {"id": str(schedule.id), "status": "updated"}


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> None:
    result = await db.execute(select(Schedule).where(Schedule.id == schedule_id))
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    await db.delete(schedule)
