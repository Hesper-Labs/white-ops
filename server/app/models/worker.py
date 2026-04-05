from datetime import datetime

from sqlalchemy import String, Integer, Boolean, DateTime, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Worker(Base):
    __tablename__ = "workers"

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hostname: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[str] = mapped_column(String(45))
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, online, offline, error
    is_approved: Mapped[bool] = mapped_column(Boolean, default=False)
    group: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Capacity
    max_agents: Mapped[int] = mapped_column(Integer, default=5)
    cpu_cores: Mapped[int] = mapped_column(Integer, default=0)
    memory_total_mb: Mapped[int] = mapped_column(Integer, default=0)

    # Real-time stats
    cpu_usage_percent: Mapped[float] = mapped_column(Float, default=0.0)
    memory_usage_percent: Mapped[float] = mapped_column(Float, default=0.0)
    disk_usage_percent: Mapped[float] = mapped_column(Float, default=0.0)

    # Heartbeat
    last_heartbeat: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # System info
    os_info: Mapped[dict] = mapped_column(JSONB, default=dict)
    docker_version: Mapped[str | None] = mapped_column(String(50), nullable=True)

    agents = relationship("Agent", back_populates="worker")
