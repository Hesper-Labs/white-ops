import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Float, Index, String, Boolean, Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        Index("ix_agents_status_active", "status", "is_active"),
        Index("ix_agents_worker", "worker_id"),
        CheckConstraint(
            "status IN ('idle', 'busy', 'error', 'offline', 'paused', 'maintenance')",
            name="ck_agents_status",
        ),
    )

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(String(100), default="general")
    status: Mapped[str] = mapped_column(
        String(50), default="idle"
    )  # idle, busy, error, offline, paused, maintenance
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

    # Enterprise tracking fields
    last_active_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    average_task_duration_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0)
    tags: Mapped[dict] = mapped_column(JSONB, default=list)

    # Autonomy & Safety
    autonomy_level: Mapped[str] = mapped_column(String(50), default="autonomous")
    # Values: autonomous, cautious, supervised, read_only
    tool_blacklist: Mapped[dict] = mapped_column(JSONB, default=list)  # blocked tool names
    risk_rules: Mapped[dict] = mapped_column(JSONB, default=dict)
    # Example: {"max_file_delete_mb": 100, "require_approval_for": ["shell", "docker_ops"], "block_external_api": false}
    daily_budget_usd: Mapped[float] = mapped_column(Float, default=0.0)  # 0 = unlimited
    max_tokens_per_task: Mapped[int] = mapped_column(Integer, default=0)  # 0 = unlimited

    tasks = relationship("Task", back_populates="agent")
