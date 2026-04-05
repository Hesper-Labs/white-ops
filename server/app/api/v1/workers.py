"""Worker management API - registration, heartbeat, task dispatch."""

import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.worker import Worker
from app.models.agent import Agent
from app.models.task import Task

router = APIRouter()


class WorkerRegisterRequest(BaseModel):
    name: str
    hostname: str
    ip_address: str
    max_agents: int = 5
    cpu_cores: int = 0
    memory_total_mb: int = 0
    os_info: dict = {}
    docker_version: str | None = None


class HeartbeatRequest(BaseModel):
    cpu_usage_percent: float = 0.0
    memory_usage_percent: float = 0.0
    disk_usage_percent: float = 0.0


@router.post("/register")
async def register_worker(
    data: WorkerRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Register a new worker node. Requires admin approval before receiving tasks."""
    # Check if worker already registered
    result = await db.execute(select(Worker).where(Worker.name == data.name))
    existing = result.scalar_one_or_none()

    if existing:
        # Re-registration: update info and set online
        existing.hostname = data.hostname
        existing.ip_address = data.ip_address
        existing.cpu_cores = data.cpu_cores
        existing.memory_total_mb = data.memory_total_mb
        existing.os_info = data.os_info
        existing.last_heartbeat = datetime.now(timezone.utc)
        if existing.is_approved:
            existing.status = "online"
        await db.flush()
        return {"id": str(existing.id), "status": existing.status, "is_approved": existing.is_approved}

    worker = Worker(
        name=data.name,
        hostname=data.hostname,
        ip_address=data.ip_address,
        max_agents=data.max_agents,
        cpu_cores=data.cpu_cores,
        memory_total_mb=data.memory_total_mb,
        os_info=data.os_info,
        docker_version=data.docker_version,
        last_heartbeat=datetime.now(timezone.utc),
        status="pending",
    )
    db.add(worker)
    await db.flush()
    await db.refresh(worker)
    return {"id": str(worker.id), "status": "pending", "is_approved": False}


@router.post("/{worker_id}/heartbeat")
async def worker_heartbeat(
    worker_id: uuid.UUID,
    data: HeartbeatRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update worker heartbeat and system metrics."""
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")

    worker.cpu_usage_percent = data.cpu_usage_percent
    worker.memory_usage_percent = data.memory_usage_percent
    worker.disk_usage_percent = data.disk_usage_percent
    worker.last_heartbeat = datetime.now(timezone.utc)

    if worker.is_approved and worker.status != "online":
        worker.status = "online"

    await db.flush()
    return {"status": worker.status}


@router.get("/{worker_id}/tasks")
async def get_worker_tasks(
    worker_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    """Get pending tasks assigned to agents on this worker."""
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker or not worker.is_approved:
        return []

    # Get agents on this worker
    agents_result = await db.execute(
        select(Agent).where(Agent.worker_id == worker_id, Agent.is_active.is_(True))
    )
    agents = {a.id: a for a in agents_result.scalars().all()}

    if not agents:
        # Auto-assign: get unassigned tasks and assign to available agents
        unassigned = await db.execute(
            select(Task).where(Task.status == "pending", Task.agent_id.is_(None)).limit(5)
        )
        tasks_to_assign = list(unassigned.scalars().all())

        # Get all idle agents on this worker
        idle_agents = [a for a in agents.values() if a.status == "idle"]
        assigned_tasks = []

        for task, agent in zip(tasks_to_assign, idle_agents):
            task.agent_id = agent.id
            task.status = "assigned"
            assigned_tasks.append(task)
            agent.status = "busy"

        if assigned_tasks:
            await db.flush()

    # Get tasks assigned to this worker's agents
    tasks_result = await db.execute(
        select(Task).where(
            Task.agent_id.in_(list(agents.keys())),
            Task.status.in_(["assigned", "pending"]),
        ).limit(10)
    )
    tasks = tasks_result.scalars().all()

    return [
        {
            "id": str(t.id),
            "title": t.title,
            "description": t.description,
            "instructions": t.instructions,
            "priority": t.priority,
            "agent_id": str(t.agent_id) if t.agent_id else None,
            "required_tools": t.required_tools,
            "max_retries": t.max_retries,
        }
        for t in tasks
    ]


@router.get("/overview")
async def workers_overview(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get fleet overview stats."""
    total = await db.execute(select(func.count(Worker.id)))
    online = await db.execute(
        select(func.count(Worker.id)).where(Worker.status == "online")
    )
    pending = await db.execute(
        select(func.count(Worker.id)).where(Worker.status == "pending")
    )

    # Detect offline workers (no heartbeat in 2 minutes)
    threshold = datetime.now(timezone.utc) - timedelta(minutes=2)
    stale = await db.execute(
        select(Worker).where(
            Worker.status == "online",
            Worker.last_heartbeat < threshold,
        )
    )
    for worker in stale.scalars().all():
        worker.status = "offline"

    total_cpu = await db.execute(select(func.sum(Worker.cpu_cores)).where(Worker.status == "online"))
    total_mem = await db.execute(select(func.sum(Worker.memory_total_mb)).where(Worker.status == "online"))
    total_agents = await db.execute(
        select(func.count(Agent.id)).where(Agent.is_active.is_(True))
    )

    return {
        "total_workers": total.scalar() or 0,
        "online_workers": online.scalar() or 0,
        "pending_workers": pending.scalar() or 0,
        "total_cpu_cores": total_cpu.scalar() or 0,
        "total_memory_mb": total_mem.scalar() or 0,
        "total_active_agents": total_agents.scalar() or 0,
    }
