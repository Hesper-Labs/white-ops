"""Export/Import API - backup and restore system configuration."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.db.session import get_db
from app.models.agent import Agent
from app.models.task import Task
from app.models.workflow import Workflow
from app.models.settings import KnowledgeBase, SystemSettings
from app.models.user import User

router = APIRouter()


@router.get("/agents")
async def export_agents(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Export all agent configurations as JSON."""
    result = await db.execute(select(Agent))
    agents = result.scalars().all()
    return {
        "export_type": "agents",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "count": len(agents),
        "data": [
            {
                "name": a.name,
                "description": a.description,
                "role": a.role,
                "llm_provider": a.llm_provider,
                "llm_model": a.llm_model,
                "system_prompt": a.system_prompt,
                "temperature": a.temperature,
                "max_tokens": a.max_tokens,
                "enabled_tools": a.enabled_tools,
                "max_concurrent_tasks": a.max_concurrent_tasks,
            }
            for a in agents
        ],
    }


@router.get("/settings")
async def export_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Export all system settings."""
    result = await db.execute(select(SystemSettings))
    settings = result.scalars().all()
    return {
        "export_type": "settings",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "count": len(settings),
        "data": [
            {
                "key": s.key,
                "value": s.value if not s.is_secret else "***",
                "category": s.category,
            }
            for s in settings
        ],
    }


@router.get("/knowledge")
async def export_knowledge(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Export knowledge base."""
    result = await db.execute(select(KnowledgeBase))
    entries = result.scalars().all()
    return {
        "export_type": "knowledge",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "count": len(entries),
        "data": [
            {
                "title": k.title,
                "content": k.content,
                "category": k.category,
                "tags": k.tags,
                "source": k.source,
            }
            for k in entries
        ],
    }


@router.get("/full")
async def export_full(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Export full system backup (agents + settings + knowledge)."""
    agents = await export_agents(db=db, user=user)
    settings = await export_settings(db=db, user=user)
    knowledge = await export_knowledge(db=db, user=user)
    return {
        "export_type": "full",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "agents": agents["data"],
        "settings": settings["data"],
        "knowledge": knowledge["data"],
    }


@router.post("/import/agents")
async def import_agents(
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Import agent configurations from JSON."""
    content = await file.read()
    data = json.loads(content)
    agents_data = data.get("data", data.get("agents", []))
    imported = 0

    for agent_data in agents_data:
        existing = await db.execute(
            select(Agent).where(Agent.name == agent_data["name"])
        )
        if existing.scalar_one_or_none():
            continue

        agent = Agent(**{k: v for k, v in agent_data.items() if hasattr(Agent, k)})
        db.add(agent)
        imported += 1

    await db.flush()
    return {"imported": imported, "total": len(agents_data)}
