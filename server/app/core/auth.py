"""Authentication dependencies: user retrieval, MFA, lockout, permissions."""

import uuid
from datetime import UTC, datetime, timedelta

import redis.asyncio as aioredis
import structlog
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.permissions import has_permission
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

logger = structlog.get_logger()

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)

# Redis client for token revocation checks (lazy-initialized)
_revocation_redis: aioredis.Redis | None = None

# Lockout configuration
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 15


async def _get_revocation_redis() -> aioredis.Redis | None:
    """Get or create Redis client for token revocation checks."""
    global _revocation_redis
    if _revocation_redis is None:
        try:
            _revocation_redis = aioredis.from_url(
                settings.redis_url, decode_responses=True
            )
            await _revocation_redis.ping()
        except Exception as exc:
            logger.warning("redis_revocation_check_unavailable", error=str(exc))
            _revocation_redis = None
    return _revocation_redis


async def _is_token_revoked(token: str) -> bool:
    """Check if a token has been revoked via Redis.

    SECURITY: If Redis is unavailable, we DENY the request rather than allowing
    potentially revoked tokens through. This is fail-closed behavior.
    """
    redis_client = await _get_revocation_redis()
    if redis_client is None:
        logger.error(
            "redis_revocation_unavailable",
            detail="Denying request because token revocation check is unavailable",
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable. Please try again.",
        )
    try:
        return await redis_client.exists(f"revoked_token:{token}") > 0
    except Exception as exc:
        logger.error("redis_revocation_check_failed", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service temporarily unavailable. Please try again.",
        ) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate JWT and return the authenticated user.

    Checks: token decode, iat/aud/iss claims, token type, revocation, user active.
    """
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        token_type = payload.get("type")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing subject"
            )
        if token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
            )
        if "iat" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token: missing iat"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from None

    # Check token revocation
    if await _is_token_revoked(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked"
        )

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
        )
    return user


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: AsyncSession = Depends(get_db),
) -> User | None:
    """Like get_current_user but returns None if no token is provided.

    Useful for endpoints that behave differently for authenticated vs anonymous users.
    """
    if credentials is None:
        return None

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id or payload.get("type") != "access":
            return None
    except JWTError:
        return None

    if await _is_token_revoked(credentials.credentials):
        return None

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        return None
    return user


# ---- Role-based Dependencies ----


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return user


async def require_operator(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("admin", "operator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Operator access required"
        )
    return user


def require_permission(permission: str):
    """Dependency factory: creates a dependency that checks a specific permission.

    Usage:
        @router.get("/secrets", dependencies=[Depends(require_permission("secrets:read"))])
    """

    async def _check_permission(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission}",
            )
        return user

    return _check_permission


# ---- MFA Verification ----


async def require_mfa_verified(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Check that MFA is verified for the current session if MFA is enabled.

    If the user has MFA enabled, their JWT must contain mfa_verified=True.
    """
    from app.models.security import UserMFA

    result = await db.execute(
        select(UserMFA).where(UserMFA.user_id == user.id, UserMFA.is_enabled.is_(True))
    )
    mfa_record = result.scalar_one_or_none()

    if mfa_record is not None:
        # MFA is enabled -- check Redis for verification status
        redis_client = await _get_revocation_redis()
        if redis_client is None:
            logger.error("redis_mfa_unavailable", user_id=str(user.id))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MFA verification service temporarily unavailable.",
            )
        try:
            mfa_ok = await redis_client.get(f"mfa_verified:{user.id}")
            if not mfa_ok:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="MFA verification required",
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("redis_mfa_check_failed", error=str(exc), user_id=str(user.id))
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MFA verification service temporarily unavailable.",
            ) from exc

    return user


# ---- Account Lockout ----


async def check_account_lockout(email: str, db: AsyncSession) -> bool:
    """Check if an account is locked due to too many failed login attempts.

    Returns True if the account is locked (caller should deny login).
    """
    from app.models.security import LoginAttempt

    cutoff = datetime.now(UTC) - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
    result = await db.execute(
        select(func.count())
        .select_from(LoginAttempt)
        .where(
            LoginAttempt.email == email,
            LoginAttempt.success.is_(False),
            LoginAttempt.attempted_at >= cutoff,
        )
    )
    failed_count = result.scalar() or 0
    return failed_count >= MAX_FAILED_ATTEMPTS


async def record_login_attempt(
    email: str, success: bool, ip: str, db: AsyncSession
) -> None:
    """Record a login attempt for lockout tracking and audit logging."""
    from app.models.security import LoginAttempt

    attempt = LoginAttempt(
        email=email,
        success=success,
        ip_address=ip,
        attempted_at=datetime.now(UTC),
    )
    db.add(attempt)
    await db.commit()
