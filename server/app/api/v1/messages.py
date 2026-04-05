import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.message import Message
from app.models.user import User

router = APIRouter()


class MessageSend(BaseModel):
    sender_agent_id: str
    recipient_agent_id: str
    channel: str = "direct"
    subject: str | None = None
    body: str
    attachments: list = []


@router.get("/")
async def list_messages(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    agent_id: str | None = None,
    channel: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    query = select(Message)
    if agent_id:
        uid = uuid.UUID(agent_id)
        query = query.where(
            or_(Message.sender_agent_id == uid, Message.recipient_agent_id == uid)
        )
    if channel:
        query = query.where(Message.channel == channel)
    result = await db.execute(
        query.order_by(Message.created_at.desc()).limit(limit).offset(offset)
    )
    messages = result.scalars().all()
    return [
        {
            "id": str(m.id),
            "sender_agent_id": str(m.sender_agent_id),
            "recipient_agent_id": str(m.recipient_agent_id),
            "channel": m.channel,
            "subject": m.subject,
            "body": m.body,
            "is_read": m.is_read,
            "attachments": m.attachments,
            "created_at": str(m.created_at),
        }
        for m in messages
    ]


@router.post("/send")
async def send_message(
    data: MessageSend,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    msg = Message(
        sender_agent_id=uuid.UUID(data.sender_agent_id),
        recipient_agent_id=uuid.UUID(data.recipient_agent_id),
        channel=data.channel,
        subject=data.subject,
        body=data.body,
        attachments=data.attachments,
    )
    db.add(msg)
    await db.flush()
    await db.refresh(msg)
    return {"id": str(msg.id), "status": "sent"}


@router.patch("/{message_id}/read")
async def mark_read(
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    result = await db.execute(select(Message).where(Message.id == message_id))
    msg = result.scalar_one_or_none()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.is_read = True
    await db.flush()
    return {"id": str(msg.id), "is_read": True}
