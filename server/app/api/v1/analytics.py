"""Analytics API - performance metrics, cost tracking, and reporting."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.agent import Agent
from app.models.file import File
from app.models.message import Message
from app.models.task import Task
from app.models.user import User
from app.models.worker import Worker

router = APIRouter()


@router.get("/overview")
async def analytics_overview(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    days: int = 7,
) -> dict:
    """Get platform analytics for the given period."""
    since = datetime.now(UTC) - timedelta(days=days)

    # Tasks
    total_tasks = await db.execute(
        select(func.count(Task.id)).where(Task.created_at >= since)
    )
    completed_tasks = await db.execute(
        select(func.count(Task.id)).where(
            Task.status == "completed", Task.created_at >= since
        )
    )
    failed_tasks = await db.execute(
        select(func.count(Task.id)).where(
            Task.status == "failed", Task.created_at >= since
        )
    )

    # Average completion time
    avg_time = await db.execute(
        select(
            func.avg(
                func.extract("epoch", Task.completed_at) - func.extract("epoch", Task.started_at)
            )
        ).where(
            Task.status == "completed",
            Task.completed_at.isnot(None),
            Task.started_at.isnot(None),
            Task.created_at >= since,
        )
    )

    # Messages
    total_messages = await db.execute(
        select(func.count(Message.id)).where(Message.created_at >= since)
    )

    # Files
    total_files = await db.execute(
        select(func.count(File.id)).where(File.created_at >= since)
    )
    total_file_size = await db.execute(
        select(func.sum(File.size_bytes)).where(File.created_at >= since)
    )

    total = total_tasks.scalar() or 0
    completed = completed_tasks.scalar() or 0

    return {
        "period_days": days,
        "tasks": {
            "total": total,
            "completed": completed,
            "failed": failed_tasks.scalar() or 0,
            "success_rate": round(completed / max(total, 1) * 100, 1),
            "avg_completion_seconds": round(avg_time.scalar() or 0, 1),
        },
        "messages": {
            "total": total_messages.scalar() or 0,
        },
        "files": {
            "total": total_files.scalar() or 0,
            "total_size_bytes": total_file_size.scalar() or 0,
        },
    }


@router.get("/agents")
async def agent_analytics(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    """Get performance analytics for each agent."""
    result = await db.execute(select(Agent).order_by(Agent.tasks_completed.desc()))
    agents = result.scalars().all()

    analytics = []
    for agent in agents:
        total = agent.tasks_completed + agent.tasks_failed
        analytics.append({
            "id": str(agent.id),
            "name": agent.name,
            "role": agent.role,
            "status": agent.status,
            "tasks_completed": agent.tasks_completed,
            "tasks_failed": agent.tasks_failed,
            "total_tasks": total,
            "success_rate": round(agent.tasks_completed / max(total, 1) * 100, 1),
            "llm_provider": agent.llm_provider,
            "llm_model": agent.llm_model,
        })

    return analytics


@router.get("/tasks/timeline")
async def task_timeline(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    days: int = 30,
) -> list[dict]:
    """Get task creation timeline for charting."""
    since = datetime.now(UTC) - timedelta(days=days)

    result = await db.execute(
        select(
            func.date_trunc("day", Task.created_at).label("day"),
            func.count(Task.id).label("total"),
            func.count(Task.id).filter(Task.status == "completed").label("completed"),
            func.count(Task.id).filter(Task.status == "failed").label("failed"),
        )
        .where(Task.created_at >= since)
        .group_by(func.date_trunc("day", Task.created_at))
        .order_by(func.date_trunc("day", Task.created_at))
    )

    return [
        {
            "date": str(row.day),
            "total": row.total,
            "completed": row.completed,
            "failed": row.failed,
        }
        for row in result.all()
    ]


@router.get("/workers/utilization")
async def worker_utilization(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    """Get resource utilization for each worker."""
    result = await db.execute(
        select(Worker).where(Worker.status == "online")
    )
    workers = result.scalars().all()

    utilization = []
    for w in workers:
        agent_count = await db.execute(
            select(func.count(Agent.id)).where(Agent.worker_id == w.id, Agent.is_active.is_(True))
        )
        busy_count = await db.execute(
            select(func.count(Agent.id)).where(Agent.worker_id == w.id, Agent.status == "busy")
        )

        utilization.append({
            "id": str(w.id),
            "name": w.name,
            "ip_address": w.ip_address,
            "cpu_percent": w.cpu_usage_percent,
            "memory_percent": w.memory_usage_percent,
            "disk_percent": w.disk_usage_percent,
            "agents_active": agent_count.scalar() or 0,
            "agents_busy": busy_count.scalar() or 0,
            "max_agents": w.max_agents,
            "capacity_percent": round((agent_count.scalar() or 0) / max(w.max_agents, 1) * 100, 1),
        })

    return utilization
