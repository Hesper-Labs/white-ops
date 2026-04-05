import uuid

from sqlalchemy import String, Boolean, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Agent(Base):
    __tablename__ = "agents"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(100), default="general")
    status: Mapped[str] = mapped_column(
        String(50), default="idle"
    )  # idle, busy, error, offline, paused
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # LLM configuration
    llm_provider: Mapped[str] = mapped_column(String(50), default="anthropic")
    llm_model: Mapped[str] = mapped_column(String(100), default="claude-sonnet-4-20250514")
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    temperature: Mapped[float] = mapped_column(default=0.7)
    max_tokens: Mapped[int] = mapped_column(Integer, default=4096)

    # Tools enabled for this agent
    enabled_tools: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Worker assignment
    worker_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workers.id"), nullable=True
    )
    worker = relationship("Worker", back_populates="agents")

    # Resource limits
    max_concurrent_tasks: Mapped[int] = mapped_column(Integer, default=3)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, default=512)

    # Stats
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0)
    tasks_failed: Mapped[int] = mapped_column(Integer, default=0)

    # Email
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)

    tasks = relationship("Task", back_populates="agent")
