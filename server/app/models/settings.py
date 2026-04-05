from sqlalchemy import String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SystemSettings(Base):
    __tablename__ = "system_settings"

    key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    value: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), index=True)  # llm, email, security, general
    is_secret: Mapped[bool] = mapped_column(default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class KnowledgeBase(Base):
    """Shared knowledge base for agents - RAG-style memory."""

    __tablename__ = "knowledge_base"

    title: Mapped[str] = mapped_column(String(500), index=True)
    content: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(100), index=True)
    tags: Mapped[dict] = mapped_column(JSONB, default=list)
    source: Mapped[str | None] = mapped_column(String(500), nullable=True)
    embedding: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class AgentCollaboration(Base):
    """Track multi-agent collaboration sessions."""

    __tablename__ = "agent_collaborations"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active")
    participants: Mapped[dict] = mapped_column(JSONB, default=list)  # list of agent IDs
    shared_context: Mapped[dict] = mapped_column(JSONB, default=dict)
    messages: Mapped[dict] = mapped_column(JSONB, default=list)
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)


class AgentPerformance(Base):
    """Performance analytics per agent."""

    __tablename__ = "agent_performance"

    agent_id: Mapped[str] = mapped_column(String(255), index=True)
    period: Mapped[str] = mapped_column(String(50))  # daily, weekly, monthly
    period_start: Mapped[str] = mapped_column(String(50))
    tasks_completed: Mapped[int] = mapped_column(default=0)
    tasks_failed: Mapped[int] = mapped_column(default=0)
    avg_completion_time_seconds: Mapped[float] = mapped_column(default=0.0)
    tools_used: Mapped[dict] = mapped_column(JSONB, default=dict)
    tokens_consumed: Mapped[int] = mapped_column(default=0)
    cost_usd: Mapped[float] = mapped_column(default=0.0)
    quality_score: Mapped[float] = mapped_column(default=0.0)
