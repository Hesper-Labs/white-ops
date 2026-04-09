"""Memory model for agent memory service."""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Memory(Base):
    __tablename__ = "memories"

    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), index=True
    )
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), index=True)  # fact, preference, procedure, context
    importance: Mapped[int] = mapped_column(Integer, default=5)  # 1-10 scale
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
