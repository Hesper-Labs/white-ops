from datetime import datetime

from sqlalchemy import CheckConstraint, Index, String, Integer, Boolean, DateTime, Float, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Worker(Base):
    __tablename__ = "workers"
    __table_args__ = (
        Index("ix_workers_status", "status"),
        CheckConstraint(
            "status IN ('pending', 'online', 'offline', 'error', 'maintenance')",
            name="ck_workers_status",
        ),
    )

    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hostname: Mapped[str] = mapped_column(String(255))
    ip_address: Mapped[str] = mapped_column(String(45))
    status: Mapped[str] = mapped_column(
        String(50), default="pending"
    )  # pending, online, offline, error, maintenance
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

    # Enterprise fields
    gpu_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    network_bandwidth_mbps: Mapped[float] = mapped_column(Float, default=0.0)
    uptime_seconds: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    capabilities: Mapped[dict] = mapped_column(JSONB, default=dict)

    agents = relationship("Agent", back_populates="worker")
