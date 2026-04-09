"""Agent Collaboration API - multi-agent collaboration sessions."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.settings import AgentCollaboration
from app.models.user import User

router = APIRouter()


class CollaborationCreate(BaseModel):
    name: str
    description: str | None = None
    participants: list[str]  # agent IDs
    task_id: str | None = None
    initial_context: dict = {}


class CollaborationMessage(BaseModel):
    agent_id: str
    message: str
    message_type: str = "text"  # text, decision, question, action, result


@router.get("/")
async def list_collaborations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    status: str | None = None,
) -> dict:
    query = select(AgentCollaboration)
    if status:
        query = query.where(AgentCollaboration.status == status)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    result = await db.execute(
        query.order_by(AgentCollaboration.created_at.desc()).offset(skip).limit(limit)
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": str(c.id),
                "name": c.name,
                "description": c.description,
                "status": c.status,
                "participants": c.participants,
                "message_count": len(c.messages) if c.messages else 0,
                "task_id": c.task_id,
                "created_at": str(c.created_at),
            }
            for c in items
        ],
        "total": total,
    }


@router.post("/", status_code=201)
async def create_collaboration(
    data: CollaborationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    collab = AgentCollaboration(
        name=data.name,
        description=data.description,
        participants=data.participants,
        shared_context=data.initial_context,
        task_id=data.task_id,
        messages=[],
    )
    db.add(collab)
    await db.flush()
    await db.refresh(collab)
    return {"id": str(collab.id), "name": collab.name, "status": collab.status}


@router.get("/{collab_id}")
async def get_collaboration(
    collab_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(AgentCollaboration).where(AgentCollaboration.id == collab_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Collaboration not found")
    return {
        "id": str(c.id),
        "name": c.name,
        "description": c.description,
        "status": c.status,
        "participants": c.participants,
        "shared_context": c.shared_context,
        "messages": c.messages,
        "task_id": c.task_id,
        "created_at": str(c.created_at),
    }


@router.post("/{collab_id}/messages")
async def add_message(
    collab_id: uuid.UUID,
    data: CollaborationMessage,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(AgentCollaboration).where(AgentCollaboration.id == collab_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Collaboration not found")

    from datetime import datetime, timezone

    msg = {
        "agent_id": data.agent_id,
        "message": data.message,
        "type": data.message_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    messages = list(c.messages) if c.messages else []
    messages.append(msg)
    c.messages = messages
    await db.flush()
    return {"status": "sent", "message_count": len(messages)}


@router.post("/{collab_id}/context")
async def update_shared_context(
    collab_id: uuid.UUID,
    context: dict,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(
        select(AgentCollaboration).where(AgentCollaboration.id == collab_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Collaboration not found")

    current = dict(c.shared_context) if c.shared_context else {}
    current.update(context)
    c.shared_context = current
    await db.flush()
    return {"status": "updated", "context_keys": list(current.keys())}


@router.post("/{collab_id}/close")
async def close_collaboration(
    collab_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(
        select(AgentCollaboration).where(AgentCollaboration.id == collab_id)
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Collaboration not found")
    c.status = "completed"
    await db.flush()
    return {"status": "completed"}
