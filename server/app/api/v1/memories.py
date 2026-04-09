"""Agent Memory/Intelligence API - manage agent memories with search and statistics."""

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_operator
from app.db.session import get_db
from app.models.user import User
from app.services.memory_service import memory_service

logger = structlog.get_logger()
router = APIRouter()


@router.get("/{agent_id}/memories")
async def list_agent_memories(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    search: str | None = None,
    category: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List memories for an agent with optional search and category filter."""
    if search:
        memories = await memory_service.search_memories(
            db=db,
            agent_id=agent_id,
            query=search,
            category=category,
            limit=limit + skip,
        )
    else:
        memories = await memory_service.get_memories(
            db=db,
            agent_id=agent_id,
            category=category,
            limit=limit + skip,
        )

    total = len(memories)
    paged = memories[skip : skip + limit]
    return {"items": paged, "total": total, "skip": skip, "limit": limit}


@router.post("/{agent_id}/memories", status_code=status.HTTP_201_CREATED)
async def store_memory(
    agent_id: uuid.UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Store a new memory for an agent."""
    content = data.get("content")
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'content' is required",
        )

    memory = await memory_service.store_memory(
        db=db,
        agent_id=agent_id,
        content=content,
        category=data.get("category", "general"),
        importance=data.get("importance", 5),
        metadata=data.get("metadata"),
    )

    logger.info("memory_stored_via_api", memory_id=str(memory.id), agent_id=str(agent_id))
    return {
        "id": str(memory.id),
        "agent_id": str(memory.agent_id),
        "content": memory.content,
        "category": memory.category,
        "importance": memory.importance,
        "created_at": memory.created_at.isoformat(),
    }


@router.put("/memories/{memory_id}")
async def update_memory(
    memory_id: uuid.UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Update a memory's content or importance."""
    result = await memory_service.update_memory(
        db=db,
        memory_id=memory_id,
        content=data.get("content"),
        importance=data.get("importance"),
    )
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    logger.info("memory_updated_via_api", memory_id=str(memory_id))
    return result


@router.delete("/memories/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(
    memory_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> None:
    """Delete a single memory."""
    deleted = await memory_service.delete_memory(db, memory_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory not found")

    logger.info("memory_deleted_via_api", memory_id=str(memory_id))


@router.delete("/{agent_id}/memories", status_code=status.HTTP_200_OK)
async def clear_agent_memories(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Clear all memories for a specific agent."""
    count = await memory_service.clear_agent_memories(db, agent_id)
    logger.info("agent_memories_cleared", agent_id=str(agent_id), count=count)
    return {"deleted_count": count, "agent_id": str(agent_id)}


@router.get("/{agent_id}/memory-stats")
async def get_memory_stats(
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Get memory statistics for an agent."""
    stats = await memory_service.get_memory_stats(db, agent_id)
    return stats
