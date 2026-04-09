"""Marketplace API - browse and install agent templates."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.agent import Agent
from app.models.template import AgentTemplate
from app.models.user import User

router = APIRouter()


@router.get("/templates")
async def list_templates(
    category: str | None = Query(None),
    search: str | None = Query(None),
    sort_by: str = Query("downloads", regex="^(rating|downloads|name|created_at)$"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """List available agent templates with optional filtering."""
    query = select(AgentTemplate).where(AgentTemplate.active_filter())

    if category:
        query = query.where(AgentTemplate.category == category)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            AgentTemplate.name.ilike(pattern)
            | AgentTemplate.description.ilike(pattern)
        )

    if sort_by == "rating":
        query = query.order_by(AgentTemplate.rating.desc())
    elif sort_by == "downloads":
        query = query.order_by(AgentTemplate.downloads.desc())
    elif sort_by == "name":
        query = query.order_by(AgentTemplate.name.asc())
    else:
        query = query.order_by(AgentTemplate.created_at.desc())

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    results = (await db.execute(query.offset(skip).limit(limit))).scalars().all()
    return {
        "data": [
            {
                "id": str(t.id),
                "name": t.name,
                "description": t.description,
                "category": t.category,
                "icon": t.icon,
                "author": t.author,
                "is_official": t.is_official,
                "version": t.version,
                "rating": t.rating,
                "downloads": t.downloads,
                "tags": t.tags,
                "config": t.config,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in results
        ],
        "total": total,
    }


@router.get("/templates/{template_id}")
async def get_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Get a single template by ID."""
    result = await db.execute(
        select(AgentTemplate).where(
            AgentTemplate.id == template_id,
            AgentTemplate.active_filter(),
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "data": {
            "id": str(template.id),
            "name": template.name,
            "description": template.description,
            "category": template.category,
            "icon": template.icon,
            "author": template.author,
            "is_official": template.is_official,
            "version": template.version,
            "rating": template.rating,
            "downloads": template.downloads,
            "tags": template.tags,
            "config": template.config,
            "created_at": template.created_at.isoformat() if template.created_at else None,
        }
    }


@router.post("/templates/{template_id}/install")
async def install_template(
    template_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Install a template by creating an agent from its configuration."""
    result = await db.execute(
        select(AgentTemplate).where(
            AgentTemplate.id == template_id,
            AgentTemplate.active_filter(),
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Create agent from template config
    config = template.config or {}
    agent = Agent(
        name=config.get("name", template.name),
        role=config.get("role", template.category),
        description=template.description,
        status="idle",
        model=config.get("model", "claude-sonnet-4-20250514"),
        system_prompt=config.get("system_prompt", f"You are a {template.name} agent."),
        enabled_tools=config.get("tools", []),
        created_by=user.id,
    )
    db.add(agent)

    # Bump download count
    template.downloads = (template.downloads or 0) + 1

    await db.commit()
    await db.refresh(agent)

    return {
        "data": {
            "agent_id": str(agent.id),
            "template_id": str(template.id),
            "message": f"Agent '{agent.name}' created from template.",
        }
    }


@router.post("/templates", status_code=status.HTTP_201_CREATED)
async def publish_template(
    name: str = Query(...),
    description: str = Query(""),
    category: str = Query("general"),
    icon: str = Query(""),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Publish a new agent template to the marketplace."""
    template = AgentTemplate(
        name=name,
        description=description,
        category=category,
        icon=icon,
        author=user.full_name or user.email,
        is_official=False,
        is_public=True,
        version="1.0.0",
        rating=0.0,
        downloads=0,
        tags=[],
        config={},
        created_by=user.id,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    return {
        "data": {
            "id": str(template.id),
            "name": template.name,
            "message": "Template published successfully.",
        }
    }
