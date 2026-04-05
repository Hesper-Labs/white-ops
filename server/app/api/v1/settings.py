"""System settings API - manage all platform configuration from admin panel."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_admin
from app.db.session import get_db
from app.models.settings import SystemSettings
from app.models.user import User

router = APIRouter()

# Default settings that get created on first access
DEFAULT_SETTINGS = {
    "llm": {
        "default_provider": ("anthropic", "Default LLM provider", False),
        "default_model": ("claude-sonnet-4-20250514", "Default LLM model", False),
        "anthropic_api_key": ("", "Anthropic API key", True),
        "openai_api_key": ("", "OpenAI API key", True),
        "google_api_key": ("", "Google API key", True),
        "ollama_base_url": ("http://host.docker.internal:11434", "Ollama base URL", False),
        "max_tokens": ("4096", "Default max tokens per request", False),
        "temperature": ("0.7", "Default temperature", False),
    },
    "email": {
        "smtp_host": ("", "External SMTP host", False),
        "smtp_port": ("587", "External SMTP port", False),
        "smtp_user": ("", "SMTP username", False),
        "smtp_password": ("", "SMTP password", True),
        "smtp_from": ("", "From address for outgoing emails", False),
        "imap_host": ("", "IMAP host for reading emails", False),
        "imap_port": ("993", "IMAP port", False),
        "imap_user": ("", "IMAP username", False),
        "imap_password": ("", "IMAP password", True),
    },
    "security": {
        "jwt_expire_minutes": ("1440", "JWT token expiry in minutes", False),
        "require_worker_approval": ("true", "New workers must be approved", False),
        "max_login_attempts": ("5", "Max login attempts before lockout", False),
        "sandbox_enabled": ("true", "Enable code execution sandbox", False),
        "rate_limit_per_minute": ("60", "API rate limit per user per minute", False),
    },
    "general": {
        "max_agents_per_worker": ("5", "Maximum agents per worker node", False),
        "task_timeout_minutes": ("60", "Default task timeout", False),
        "max_retries": ("3", "Default max retries for failed tasks", False),
        "auto_assign_tasks": ("true", "Automatically assign tasks to idle agents", False),
        "log_level": ("INFO", "System log level", False),
        "maintenance_mode": ("false", "Enable maintenance mode", False),
    },
    "notifications": {
        "notify_task_complete": ("true", "Notify when tasks complete", False),
        "notify_task_failed": ("true", "Notify when tasks fail", False),
        "notify_worker_offline": ("true", "Notify when workers go offline", False),
        "notify_agent_error": ("true", "Notify on agent errors", False),
        "webhook_url": ("", "Webhook URL for external notifications", False),
    },
    "storage": {
        "max_file_size_mb": ("100", "Maximum file upload size in MB", False),
        "allowed_file_types": ("*", "Allowed file extensions (* for all)", False),
        "auto_cleanup_days": ("30", "Auto-delete files older than N days (0 = never)", False),
    },
}


class SettingUpdate(BaseModel):
    value: str


class SettingsBulkUpdate(BaseModel):
    settings: dict[str, str]


@router.get("/")
async def get_all_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Get all settings grouped by category."""
    result = await db.execute(select(SystemSettings).order_by(SystemSettings.category))
    existing = {s.key: s for s in result.scalars().all()}

    # Merge defaults with stored values
    output: dict[str, dict] = {}
    for category, settings in DEFAULT_SETTINGS.items():
        output[category] = {}
        for key, (default_val, description, is_secret) in settings.items():
            full_key = f"{category}.{key}"
            stored = existing.get(full_key)
            value = stored.value if stored else default_val

            # Mask secrets
            if is_secret and value:
                display_value = value[:4] + "..." + value[-4:] if len(value) > 8 else "****"
            else:
                display_value = value

            output[category][key] = {
                "value": display_value,
                "description": description,
                "is_secret": is_secret,
                "is_default": stored is None,
            }

    return output


@router.put("/{category}/{key}")
async def update_setting(
    category: str,
    key: str,
    data: SettingUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Update a single setting."""
    full_key = f"{category}.{key}"

    # Validate category and key exist in defaults
    if category not in DEFAULT_SETTINGS or key not in DEFAULT_SETTINGS[category]:
        return {"error": f"Unknown setting: {full_key}"}

    result = await db.execute(select(SystemSettings).where(SystemSettings.key == full_key))
    setting = result.scalar_one_or_none()

    is_secret = DEFAULT_SETTINGS[category][key][2]

    if setting:
        setting.value = data.value
    else:
        setting = SystemSettings(
            key=full_key,
            value=data.value,
            category=category,
            is_secret=is_secret,
            description=DEFAULT_SETTINGS[category][key][1],
        )
        db.add(setting)

    await db.flush()
    return {"key": full_key, "status": "updated"}


@router.put("/bulk")
async def bulk_update_settings(
    data: SettingsBulkUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Update multiple settings at once."""
    updated = 0
    for full_key, value in data.settings.items():
        parts = full_key.split(".", 1)
        if len(parts) != 2:
            continue
        category, key = parts
        if category not in DEFAULT_SETTINGS or key not in DEFAULT_SETTINGS[category]:
            continue

        result = await db.execute(select(SystemSettings).where(SystemSettings.key == full_key))
        setting = result.scalar_one_or_none()

        if setting:
            setting.value = value
        else:
            setting = SystemSettings(
                key=full_key,
                value=value,
                category=category,
                is_secret=DEFAULT_SETTINGS[category][key][2],
                description=DEFAULT_SETTINGS[category][key][1],
            )
            db.add(setting)
        updated += 1

    await db.flush()
    return {"updated": updated}


@router.get("/health")
async def system_health(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Check system component health."""
    import redis as redis_lib
    from app.config import settings

    health = {}

    # Database
    try:
        await db.execute(select(SystemSettings).limit(1))
        health["database"] = {"status": "healthy", "type": "PostgreSQL"}
    except Exception as e:
        health["database"] = {"status": "unhealthy", "error": str(e)}

    # Redis
    try:
        r = redis_lib.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
        )
        r.ping()
        health["redis"] = {"status": "healthy"}
        r.close()
    except Exception as e:
        health["redis"] = {"status": "unhealthy", "error": str(e)}

    # MinIO
    try:
        from minio import Minio

        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=False,
        )
        client.list_buckets()
        health["storage"] = {"status": "healthy", "type": "MinIO"}
    except Exception as e:
        health["storage"] = {"status": "unhealthy", "error": str(e)}

    # Mail
    try:
        import socket

        sock = socket.create_connection((settings.mail_server_host, settings.mail_server_port), timeout=5)
        sock.close()
        health["mail"] = {"status": "healthy"}
    except Exception as e:
        health["mail"] = {"status": "unhealthy", "error": str(e)}

    overall = all(v.get("status") == "healthy" for v in health.values())
    return {"overall": "healthy" if overall else "degraded", "components": health}
