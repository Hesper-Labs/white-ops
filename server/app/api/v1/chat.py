"""Chat API router for the Agent Chat interface."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.agent import Agent
from app.models.conversation import ChatMessage, Conversation
from app.models.user import User

router = APIRouter()


# ---------- Schemas ----------


class ConversationCreate(BaseModel):
    agent_id: str
    title: str | None = None


class ConversationResponse(BaseModel):
    id: str
    title: str
    agent_id: str
    user_id: str
    is_active: bool
    total_tokens: int
    total_cost_usd: float
    last_message_at: str | None = None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=32000)


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    tool_calls: dict | list | None = None
    tool_results: dict | list | None = None
    tokens_used: int
    cost_usd: float
    created_at: str

    model_config = {"from_attributes": True}


# ---------- Endpoints ----------


@router.get("/conversations")
async def list_conversations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """List the current user's conversations."""
    query = select(Conversation).where(
        Conversation.user_id == user.id,
        Conversation.is_deleted.is_(False),
    )

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    result = await db.execute(
        query.order_by(Conversation.last_message_at.desc().nulls_last(), Conversation.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    conversations = result.scalars().all()

    return {
        "items": [_conv_to_dict(c) for c in conversations],
        "total": total,
    }


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
async def create_conversation(
    data: ConversationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Create a new conversation with an agent."""
    # Verify agent exists
    agent_uuid = uuid.UUID(data.agent_id)
    result = await db.execute(select(Agent).where(Agent.id == agent_uuid))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    title = data.title or f"Chat with {agent.name}"
    conversation = Conversation(
        title=title,
        agent_id=agent_uuid,
        user_id=user.id,
    )
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)

    return _conv_to_dict(conversation)


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(
    conversation_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Get messages for a conversation."""
    # Verify ownership
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    query = select(ChatMessage).where(ChatMessage.conversation_id == conversation_id)
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    result = await db.execute(
        query.order_by(ChatMessage.created_at.asc()).offset(skip).limit(limit)
    )
    messages = result.scalars().all()

    return {
        "items": [_msg_to_dict(m) for m in messages],
        "total": total,
    }


@router.post("/conversations/{conversation_id}/messages")
async def send_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Send a message in a conversation and get the agent response."""
    # Verify ownership
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    now = datetime.now(timezone.utc)

    # Store user message
    user_msg = ChatMessage(
        conversation_id=conversation_id,
        role="user",
        content=data.content,
    )
    db.add(user_msg)

    # Generate agent response (placeholder - would integrate with LLM in production)
    assistant_msg = ChatMessage(
        conversation_id=conversation_id,
        role="assistant",
        content=f"I've received your message. This is a placeholder response from the agent. In production, this would be processed by the assigned LLM.",
        tokens_used=150,
        cost_usd=0.002,
    )
    db.add(assistant_msg)

    # Update conversation metadata
    conversation.last_message_at = now
    conversation.total_tokens += 150
    conversation.total_cost_usd += 0.002

    await db.flush()
    await db.refresh(user_msg)
    await db.refresh(assistant_msg)

    return {
        "user_message": _msg_to_dict(user_msg),
        "assistant_message": _msg_to_dict(assistant_msg),
    }


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Delete (soft) a conversation."""
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.user_id == user.id,
        )
    )
    conversation = conv_result.scalar_one_or_none()
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    conversation.soft_delete()
    await db.flush()


# ---------- Helpers ----------


def _conv_to_dict(c: Conversation) -> dict:
    return {
        "id": str(c.id),
        "title": c.title,
        "agent_id": str(c.agent_id),
        "user_id": str(c.user_id),
        "is_active": c.is_active,
        "total_tokens": c.total_tokens,
        "total_cost_usd": c.total_cost_usd,
        "last_message_at": c.last_message_at.isoformat() if c.last_message_at else None,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


def _msg_to_dict(m: ChatMessage) -> dict:
    return {
        "id": str(m.id),
        "conversation_id": str(m.conversation_id),
        "role": m.role,
        "content": m.content,
        "tool_calls": m.tool_calls,
        "tool_results": m.tool_results,
        "tokens_used": m.tokens_used,
        "cost_usd": m.cost_usd,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }
