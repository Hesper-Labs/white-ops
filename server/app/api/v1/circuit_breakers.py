"""Circuit Breaker Management API - monitor and control circuit breaker states."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_admin, require_operator
from app.db.session import get_db
from app.models.user import User
from app.services.circuit_breaker import circuit_breaker

logger = structlog.get_logger()
router = APIRouter()


@router.get("/")
async def list_circuit_breakers(
    user: User = Depends(get_current_user),
) -> dict:
    """List all circuit breaker states."""
    try:
        states = await circuit_breaker.get_all_states()
        return {"items": states, "total": len(states)}
    except Exception as exc:
        logger.error("circuit_breaker_list_failed", error=str(exc))
        return {"items": [], "total": 0, "error": "Redis unavailable"}


@router.get("/config")
async def get_circuit_breaker_config(
    user: User = Depends(get_current_user),
) -> dict:
    """Get circuit breaker configuration defaults."""
    from app.services.circuit_breaker import (
        DEFAULT_FAILURE_THRESHOLD,
        DEFAULT_RECOVERY_TIMEOUT,
        DEFAULT_SUCCESS_THRESHOLD,
        DEFAULT_WINDOW_SECONDS,
    )

    return {
        "failure_threshold": DEFAULT_FAILURE_THRESHOLD,
        "recovery_timeout_seconds": DEFAULT_RECOVERY_TIMEOUT,
        "success_threshold": DEFAULT_SUCCESS_THRESHOLD,
        "window_seconds": DEFAULT_WINDOW_SECONDS,
    }


@router.put("/config")
async def update_circuit_breaker_config(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Update circuit breaker configuration defaults.

    Note: This updates the in-memory defaults. Per-service overrides
    are stored in Redis.
    """
    import app.services.circuit_breaker as cb_module

    if "failure_threshold" in data:
        cb_module.DEFAULT_FAILURE_THRESHOLD = int(data["failure_threshold"])
    if "recovery_timeout_seconds" in data:
        cb_module.DEFAULT_RECOVERY_TIMEOUT = int(data["recovery_timeout_seconds"])
    if "success_threshold" in data:
        cb_module.DEFAULT_SUCCESS_THRESHOLD = int(data["success_threshold"])
    if "window_seconds" in data:
        cb_module.DEFAULT_WINDOW_SECONDS = int(data["window_seconds"])

    logger.info("circuit_breaker_config_updated", user_id=str(user.id), changes=data)

    return {
        "failure_threshold": cb_module.DEFAULT_FAILURE_THRESHOLD,
        "recovery_timeout_seconds": cb_module.DEFAULT_RECOVERY_TIMEOUT,
        "success_threshold": cb_module.DEFAULT_SUCCESS_THRESHOLD,
        "window_seconds": cb_module.DEFAULT_WINDOW_SECONDS,
        "message": "Configuration updated",
    }


@router.get("/{service_name}")
async def get_circuit_breaker_state(
    service_name: str,
    user: User = Depends(get_current_user),
) -> dict:
    """Get the current state of a specific circuit breaker."""
    try:
        state = await circuit_breaker.get_state(service_name)
        return state
    except Exception as exc:
        logger.error("circuit_breaker_get_failed", service=service_name, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to retrieve circuit breaker state",
        ) from exc


@router.post("/{service_name}/force-open")
async def force_open_circuit(
    service_name: str,
    user: User = Depends(require_operator),
) -> dict:
    """Force a circuit breaker to the open state (block all requests)."""
    try:
        await circuit_breaker.force_open(service_name)
        logger.info("circuit_breaker_force_opened", service=service_name, user_id=str(user.id))
        return {
            "service": service_name,
            "state": "open",
            "message": f"Circuit breaker for '{service_name}' forced open",
        }
    except Exception as exc:
        logger.error("circuit_breaker_force_open_failed", service=service_name, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to force open circuit breaker",
        ) from exc


@router.post("/{service_name}/force-close")
async def force_close_circuit(
    service_name: str,
    user: User = Depends(require_operator),
) -> dict:
    """Force a circuit breaker to the closed state (allow all requests)."""
    try:
        await circuit_breaker.force_close(service_name)
        logger.info("circuit_breaker_force_closed", service=service_name, user_id=str(user.id))
        return {
            "service": service_name,
            "state": "closed",
            "message": f"Circuit breaker for '{service_name}' forced closed",
        }
    except Exception as exc:
        logger.error("circuit_breaker_force_close_failed", service=service_name, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to force close circuit breaker",
        ) from exc


@router.post("/{service_name}/reset")
async def reset_circuit_breaker(
    service_name: str,
    user: User = Depends(require_operator),
) -> dict:
    """Fully reset a circuit breaker, clearing all state and counters."""
    try:
        await circuit_breaker.reset(service_name)
        logger.info("circuit_breaker_reset", service=service_name, user_id=str(user.id))
        return {
            "service": service_name,
            "state": "closed",
            "message": f"Circuit breaker for '{service_name}' has been fully reset",
        }
    except Exception as exc:
        logger.error("circuit_breaker_reset_failed", service=service_name, error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to reset circuit breaker",
        ) from exc
