"""Knowledge Base API - shared knowledge between agents (RAG-style memory)."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.settings import KnowledgeBase
from app.models.user import User

router = APIRouter()


class KnowledgeCreate(BaseModel):
    title: str
    content: str
    category: str = "general"
    tags: list[str] = []
    source: str | None = None


class KnowledgeUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    category: str | None = None
    tags: list[str] | None = None


@router.get("/")
async def list_knowledge(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    category: str | None = None,
    search: str | None = None,
) -> dict:
    query = select(KnowledgeBase)
    if category:
        query = query.where(KnowledgeBase.category == category)
    if search:
        query = query.where(
            or_(
                KnowledgeBase.title.ilike(f"%{search}%"),
                KnowledgeBase.content.ilike(f"%{search}%"),
            )
        )

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    result = await db.execute(
        query.order_by(KnowledgeBase.created_at.desc()).offset(skip).limit(limit)
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "id": str(k.id),
                "title": k.title,
                "content": k.content[:500],
                "category": k.category,
                "tags": k.tags,
                "source": k.source,
                "created_at": str(k.created_at),
            }
            for k in items
        ],
        "total": total,
    }


@router.post("/", status_code=201)
async def create_knowledge(
    data: KnowledgeCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    entry = KnowledgeBase(
        title=data.title,
        content=data.content,
        category=data.category,
        tags=data.tags,
        source=data.source,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return {"id": str(entry.id), "title": entry.title}


@router.get("/{entry_id}")
async def get_knowledge(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == entry_id))
    k = result.scalar_one_or_none()
    if not k:
        raise HTTPException(status_code=404, detail="Knowledge entry not found")
    return {
        "id": str(k.id),
        "title": k.title,
        "content": k.content,
        "category": k.category,
        "tags": k.tags,
        "source": k.source,
        "created_at": str(k.created_at),
        "updated_at": str(k.updated_at),
    }


@router.delete("/{entry_id}", status_code=204)
async def delete_knowledge(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == entry_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Not found")
    await db.delete(entry)


@router.get("/categories")
async def list_categories(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[str]:
    from sqlalchemy import func

    result = await db.execute(
        select(KnowledgeBase.category, func.count(KnowledgeBase.id))
        .group_by(KnowledgeBase.category)
    )
    return [{"category": row[0], "count": row[1]} for row in result.all()]
