import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User
from app.models.worker import Worker
from app.models.audit import AuditLog

router = APIRouter()


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "viewer"


class WorkerApproval(BaseModel):
    is_approved: bool
    group: str | None = None


@router.get("/users")
async def list_users(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> list[dict]:
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        {
            "id": str(u.id),
            "email": u.email,
            "full_name": u.full_name,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": str(u.created_at),
        }
        for u in users
    ]


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    existing = await db.execute(select(User).where(User.email == data.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    new_user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
    )
    db.add(new_user)
    await db.flush()
    await db.refresh(new_user)
    return {"id": str(new_user.id), "email": new_user.email, "role": new_user.role}


@router.get("/workers")
async def list_workers(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> list[dict]:
    result = await db.execute(select(Worker).order_by(Worker.created_at.desc()))
    workers = result.scalars().all()
    return [
        {
            "id": str(w.id),
            "name": w.name,
            "hostname": w.hostname,
            "ip_address": w.ip_address,
            "status": w.status,
            "is_approved": w.is_approved,
            "group": w.group,
            "max_agents": w.max_agents,
            "cpu_usage_percent": w.cpu_usage_percent,
            "memory_usage_percent": w.memory_usage_percent,
            "disk_usage_percent": w.disk_usage_percent,
            "last_heartbeat": str(w.last_heartbeat) if w.last_heartbeat else None,
        }
        for w in workers
    ]


@router.patch("/workers/{worker_id}/approve")
async def approve_worker(
    worker_id: uuid.UUID,
    data: WorkerApproval,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    result = await db.execute(select(Worker).where(Worker.id == worker_id))
    worker = result.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Worker not found")
    worker.is_approved = data.is_approved
    if data.group:
        worker.group = data.group
    if data.is_approved:
        worker.status = "online"
    await db.flush()
    return {"id": str(worker.id), "is_approved": worker.is_approved, "status": worker.status}


@router.get("/audit")
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit).offset(offset)
    )
    logs = result.scalars().all()
    return [
        {
            "id": str(log.id),
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": str(log.resource_id) if log.resource_id else None,
            "actor_type": log.actor_type,
            "actor_id": str(log.actor_id) if log.actor_id else None,
            "details": log.details,
            "created_at": str(log.created_at),
        }
        for log in logs
    ]
