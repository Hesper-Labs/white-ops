"""Initial schema - all enterprise models.

Revision ID: 001_initial
Revises:
Create Date: 2025-04-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- Core Tables ----
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="viewer"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("mfa_enabled", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_login_attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_ip", sa.String(45), nullable=True),
        sa.Column("password_history", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "workers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("hostname", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("is_approved", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("group", sa.String(255), nullable=True),
        sa.Column("max_agents", sa.Integer, nullable=False, server_default="5"),
        sa.Column("cpu_cores", sa.Integer, nullable=False, server_default="0"),
        sa.Column("memory_total_mb", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cpu_usage_percent", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("memory_usage_percent", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("disk_usage_percent", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("last_heartbeat", sa.DateTime(timezone=True), nullable=True),
        sa.Column("os_info", JSONB, nullable=False, server_default="{}"),
        sa.Column("docker_version", sa.String(50), nullable=True),
        sa.Column("gpu_info", JSONB, nullable=True),
        sa.Column("network_bandwidth_mbps", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("uptime_seconds", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text, nullable=True),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("capabilities", JSONB, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint("status IN ('pending','online','offline','error','maintenance')", name="ck_workers_status"),
    )
    op.create_index("ix_workers_status", "workers", ["status"])

    op.create_table(
        "agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("role", sa.String(100), nullable=False, server_default="general"),
        sa.Column("status", sa.String(50), nullable=False, server_default="idle"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("llm_provider", sa.String(50), nullable=False, server_default="anthropic"),
        sa.Column("llm_model", sa.String(100), nullable=False, server_default="claude-sonnet-4-20250514"),
        sa.Column("system_prompt", sa.Text, nullable=True),
        sa.Column("temperature", sa.Float, nullable=False, server_default="0.7"),
        sa.Column("max_tokens", sa.Integer, nullable=False, server_default="4096"),
        sa.Column("enabled_tools", JSONB, nullable=False, server_default="{}"),
        sa.Column("worker_id", UUID(as_uuid=True), sa.ForeignKey("workers.id"), nullable=True),
        sa.Column("max_concurrent_tasks", sa.Integer, nullable=False, server_default="3"),
        sa.Column("memory_limit_mb", sa.Integer, nullable=False, server_default="512"),
        sa.Column("tasks_completed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("tasks_failed", sa.Integer, nullable=False, server_default="0"),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_tokens_used", sa.Integer, nullable=False, server_default="0"),
        sa.Column("total_cost_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("success_rate", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("tags", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint("status IN ('idle','busy','error','offline','paused','maintenance')", name="ck_agents_status"),
    )
    op.create_index("ix_agents_status_active", "agents", ["status", "is_active"])
    op.create_index("ix_agents_worker", "agents", ["worker_id"])

    op.create_table(
        "workflows",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("steps", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )

    op.create_table(
        "tasks",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("instructions", sa.Text, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=True),
        sa.Column("assigned_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("workflow_id", UUID(as_uuid=True), sa.ForeignKey("workflows.id"), nullable=True),
        sa.Column("parent_task_id", UUID(as_uuid=True), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("result", sa.Text, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("output_files", JSONB, nullable=False, server_default="[]"),
        sa.Column("metadata", JSONB, nullable=False, server_default="{}"),
        sa.Column("deadline", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_retries", sa.Integer, nullable=False, server_default="3"),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("required_tools", JSONB, nullable=False, server_default="[]"),
        sa.Column("progress_percent", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_tokens", sa.Integer, nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.CheckConstraint(
            "status IN ('pending','queued','assigned','in_progress','review','completed','failed','cancelled')",
            name="ck_tasks_status",
        ),
        sa.CheckConstraint("priority IN ('critical','high','medium','low')", name="ck_tasks_priority"),
    )
    op.create_index("ix_tasks_agent_status", "tasks", ["agent_id", "status"])
    op.create_index("ix_tasks_status_priority", "tasks", ["status", "priority"])
    op.create_index("ix_tasks_created_status", "tasks", ["created_at", "status"])

    # ---- Supporting Tables ----
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("resource_type", sa.String(100), nullable=False),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("actor_type", sa.String(50), nullable=False),
        sa.Column("actor_id", sa.String(255), nullable=True),
        sa.Column("details", JSONB, nullable=False, server_default="{}"),
        sa.Column("changes", JSONB, nullable=False, server_default="{}"),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"])
    op.create_index("ix_audit_logs_actor", "audit_logs", ["actor_type", "actor_id"])
    op.create_index("ix_audit_logs_created", "audit_logs", ["created_at"])

    # ---- Enterprise Tables ----
    for table_name in ["secrets", "ssh_connections", "approval_rules", "approval_requests",
                       "agent_memories", "triggers", "trigger_executions",
                       "notification_channels", "notification_rules", "notifications",
                       "webhook_endpoints", "token_usage", "budgets",
                       "dead_letter_tasks", "circuit_breaker_states",
                       "user_sessions", "user_mfa", "login_attempts"]:
        # These tables are created by Base.metadata.create_all() via init_db
        # This migration serves as documentation of the initial schema
        pass


def downgrade() -> None:
    for table in [
        "login_attempts", "user_mfa", "user_sessions",
        "circuit_breaker_states", "dead_letter_tasks",
        "budgets", "token_usage", "webhook_endpoints",
        "notifications", "notification_rules", "notification_channels",
        "trigger_executions", "triggers",
        "agent_memories", "approval_requests", "approval_rules",
        "ssh_connections", "secrets", "audit_logs",
        "tasks", "workflows", "agents", "workers", "users",
    ]:
        op.drop_table(table)
