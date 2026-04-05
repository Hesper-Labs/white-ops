from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.agent import Agent
from app.models.task import Task
from app.models.worker import Worker
from app.models.message import Message
from app.models.user import User

router = APIRouter()


@router.get("/overview")
async def dashboard_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    # Agent stats
    total_agents = await db.execute(select(func.count(Agent.id)))
    active_agents = await db.execute(
        select(func.count(Agent.id)).where(Agent.is_active.is_(True))
    )
    busy_agents = await db.execute(
        select(func.count(Agent.id)).where(Agent.status == "busy")
    )

    # Task stats
    total_tasks = await db.execute(select(func.count(Task.id)))
    tasks_by_status = await db.execute(
        select(Task.status, func.count(Task.id)).group_by(Task.status)
    )

    # Worker stats
    total_workers = await db.execute(select(func.count(Worker.id)))
    online_workers = await db.execute(
        select(func.count(Worker.id)).where(Worker.status == "online")
    )

    # Message stats
    total_messages = await db.execute(select(func.count(Message.id)))
    unread_messages = await db.execute(
        select(func.count(Message.id)).where(Message.is_read.is_(False))
    )

    return {
        "agents": {
            "total": total_agents.scalar() or 0,
            "active": active_agents.scalar() or 0,
            "busy": busy_agents.scalar() or 0,
        },
        "tasks": {
            "total": total_tasks.scalar() or 0,
            "by_status": dict(tasks_by_status.all()),
        },
        "workers": {
            "total": total_workers.scalar() or 0,
            "online": online_workers.scalar() or 0,
        },
        "messages": {
            "total": total_messages.scalar() or 0,
            "unread": unread_messages.scalar() or 0,
        },
    }
