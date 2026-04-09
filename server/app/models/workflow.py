import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Workflow(Base):
    __tablename__ = "workflows"

    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default="draft"
    )  # draft, active, running, completed, failed
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    config: Mapped[dict] = mapped_column(JSONB, default=dict)

    steps = relationship("WorkflowStep", back_populates="workflow", order_by="WorkflowStep.order")


class WorkflowStep(Base):
    __tablename__ = "workflow_steps"

    workflow_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("workflows.id"), index=True
    )
    workflow = relationship("Workflow", back_populates="steps")

    name: Mapped[str] = mapped_column(String(255))
    step_type: Mapped[str] = mapped_column(
        String(50), default="task"
    )  # task, condition, parallel, wait, notify
    order: Mapped[int] = mapped_column(Integer, default=0)
    config: Mapped[dict] = mapped_column(JSONB, default=dict)
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    depends_on: Mapped[dict] = mapped_column(JSONB, default=list)  # list of step IDs
    status: Mapped[str] = mapped_column(String(50), default="pending")
