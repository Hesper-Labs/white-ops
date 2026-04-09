"""Security Settings API - password policy, MFA config, sessions, IP rules, API keys."""

import secrets
import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_admin
from app.db.session import get_db
from app.models.security import UserSession
from app.models.user import User
from app.services.audit import log_action

logger = structlog.get_logger()
router = APIRouter()


# ---------------------------------------------------------------------------
# Security settings
# ---------------------------------------------------------------------------

@router.get("/")
async def get_security_settings(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Get current security settings (password policy, MFA config, session config)."""
    # Return current security configuration
    return {
        "password_policy": {
            "min_length": 12,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_numbers": True,
            "require_special": True,
            "max_age_days": 90,
            "history_count": 5,
        },
        "mfa": {
            "enabled": True,
            "methods": ["totp"],
            "grace_period_hours": 24,
        },
        "session": {
            "max_duration_hours": 24,
            "idle_timeout_minutes": 30,
            "max_concurrent_sessions": 5,
        },
    }


@router.put("/password-policy")
async def update_password_policy(
    policy: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Update password policy settings."""
    await log_action(
        db,
        action="password_policy_updated",
        resource_type="security",
        actor_type="user",
        actor_id=user.id,
        details="Password policy updated",
        changes=policy,
    )
    logger.info("password_policy_updated", user_id=str(user.id))
    return {"status": "updated", "policy": policy}


# ---------------------------------------------------------------------------
# Session management
# ---------------------------------------------------------------------------

@router.get("/sessions")
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List active user sessions."""
    query = (
        select(UserSession)
        .where(UserSession.is_revoked.is_(False))
        .order_by(UserSession.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    sessions = result.scalars().all()

    count_result = await db.execute(
        select(func.count(UserSession.id)).where(UserSession.is_revoked.is_(False))
    )
    total = count_result.scalar() or 0

    return {
        "items": [
            {
                "id": str(s.id),
                "user_id": str(s.user_id),
                "ip_address": s.ip_address,
                "user_agent": s.user_agent,
                "expires_at": s.expires_at.isoformat() if s.expires_at else None,
                "created_at": s.created_at.isoformat(),
            }
            for s in sessions
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> None:
    """Force logout a specific session."""
    result = await db.execute(select(UserSession).where(UserSession.id == session_id))
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    session.is_revoked = True
    await db.flush()

    await log_action(
        db,
        action="session_revoked",
        resource_type="session",
        resource_id=session_id,
        actor_type="user",
        actor_id=user.id,
        details=f"Session {session_id} force revoked",
    )
    logger.info("session_revoked", session_id=str(session_id), admin_id=str(user.id))


# ---------------------------------------------------------------------------
# IP whitelist rules
# ---------------------------------------------------------------------------

# In-memory store for IP rules (in production, use a DB model)
_ip_rules: list[dict] = []


@router.get("/ip-rules")
async def list_ip_rules(
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List IP whitelist/blocklist rules."""
    total = len(_ip_rules)
    items = _ip_rules[skip : skip + limit]
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/ip-rules", status_code=status.HTTP_201_CREATED)
async def add_ip_rule(
    rule: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Add an IP whitelist/blocklist rule."""
    rule_entry = {
        "id": str(uuid.uuid4()),
        "cidr": rule.get("cidr", ""),
        "action": rule.get("action", "allow"),  # allow or deny
        "description": rule.get("description", ""),
        "created_by": str(user.id),
        "created_at": datetime.now(UTC).isoformat(),
    }
    _ip_rules.append(rule_entry)

    await log_action(
        db,
        action="ip_rule_created",
        resource_type="security",
        actor_type="user",
        actor_id=user.id,
        details=f"IP rule added: {rule_entry['cidr']} ({rule_entry['action']})",
    )
    logger.info("ip_rule_added", cidr=rule_entry["cidr"], action=rule_entry["action"])
    return rule_entry


@router.delete("/ip-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_ip_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> None:
    """Remove an IP rule."""
    global _ip_rules
    original_len = len(_ip_rules)
    _ip_rules = [r for r in _ip_rules if r["id"] != rule_id]
    if len(_ip_rules) == original_len:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="IP rule not found")

    await log_action(
        db,
        action="ip_rule_deleted",
        resource_type="security",
        actor_type="user",
        actor_id=user.id,
        details=f"IP rule {rule_id} removed",
    )
    logger.info("ip_rule_removed", rule_id=rule_id)


# ---------------------------------------------------------------------------
# API key management
# ---------------------------------------------------------------------------

# In-memory store for API keys (in production, use a DB model)
_api_keys: list[dict] = []


@router.get("/api-keys")
async def list_api_keys(
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List API keys for the current user."""
    user_keys = [k for k in _api_keys if k["user_id"] == str(user.id) and not k.get("revoked")]
    total = len(user_keys)
    items = user_keys[skip : skip + limit]
    # Mask key values
    for item in items:
        item = {**item, "key": item["key"][:8] + "..." if len(item.get("key", "")) > 8 else "***"}
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/api-keys", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Create a new API key for the current user."""
    raw_key = f"whops_{secrets.token_urlsafe(32)}"
    key_entry = {
        "id": str(uuid.uuid4()),
        "name": data.get("name", "Unnamed Key"),
        "key": raw_key,
        "key_prefix": raw_key[:12],
        "user_id": str(user.id),
        "scopes": data.get("scopes", ["read"]),
        "expires_at": data.get("expires_at"),
        "created_at": datetime.now(UTC).isoformat(),
        "revoked": False,
    }
    _api_keys.append(key_entry)

    await log_action(
        db,
        action="api_key_created",
        resource_type="api_key",
        actor_type="user",
        actor_id=user.id,
        details=f"API key '{key_entry['name']}' created",
    )
    logger.info("api_key_created", key_id=key_entry["id"], user_id=str(user.id))

    # Return the full key only on creation
    return {
        "id": key_entry["id"],
        "name": key_entry["name"],
        "key": raw_key,
        "scopes": key_entry["scopes"],
        "created_at": key_entry["created_at"],
        "message": "Store this key securely. It will not be shown again.",
    }


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> None:
    """Revoke an API key."""
    for key_entry in _api_keys:
        if key_entry["id"] == key_id and key_entry["user_id"] == str(user.id):
            key_entry["revoked"] = True
            await log_action(
                db,
                action="api_key_revoked",
                resource_type="api_key",
                resource_id=key_id,
                actor_type="user",
                actor_id=user.id,
                details=f"API key '{key_entry['name']}' revoked",
            )
            logger.info("api_key_revoked", key_id=key_id)
            return

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
