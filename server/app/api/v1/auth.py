from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.auth import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    validate_password_strength,
    verify_password,
    verify_totp,
)
from app.db.session import get_db
from app.models.security import LoginAttempt, UserMFA
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LogoutRequest,
    MFARequiredResponse,
    MFAVerifyRequest,
    RefreshRequest,
    TokenResponse,
    UserResponse,
)
from app.services.audit import log_action

logger = structlog.get_logger()
router = APIRouter()

MAX_LOGIN_ATTEMPTS = getattr(settings, "max_login_attempts", 5)
LOCKOUT_DURATION_MINUTES = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _record_login_attempt(
    db: AsyncSession, email: str, success: bool, ip: str,
) -> None:
    """Persist a login attempt record."""
    db.add(LoginAttempt(email=email, success=success, ip_address=ip))
    await db.flush()


async def _issue_tokens(user: User) -> dict:
    """Create an access + refresh token pair for *user*."""
    payload = {"sub": str(user.id), "role": user.role}
    access_token = create_access_token(data=payload)
    refresh_token = create_refresh_token(data=payload)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
    }


async def _revoke_token_in_redis(token: str, ttl_seconds: int = 3600) -> None:
    """Add a token to the Redis blacklist so it cannot be reused."""
    try:
        import redis.asyncio as aioredis

        r = aioredis.from_url(settings.redis_url)
        await r.setex(f"token:blacklist:{token}", ttl_seconds, "1")
        await r.aclose()
    except Exception:
        logger.warning("redis_blacklist_failed", detail="Could not revoke token in Redis")


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------

@router.post("/login")
async def login(
    request: LoginRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = req.client.host if req.client else "unknown"

    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    # --- Account lockout check ---
    if user and user.locked_until and user.locked_until > datetime.now(UTC):
        logger.warning("login_locked", email=request.email, ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Account is temporarily locked due to too many failed login attempts.",
        )

    # --- Credential verification ---
    if not user or not verify_password(request.password, user.hashed_password):
        # Increment failed attempts if user exists
        if user:
            user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
            if user.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
                user.locked_until = datetime.now(UTC) + timedelta(
                    minutes=LOCKOUT_DURATION_MINUTES
                )
                logger.warning("account_locked", email=request.email, ip=client_ip)
            await db.flush()

        logger.warning("login_failed", email=request.email, ip=client_ip)
        await _record_login_attempt(db, request.email, success=False, ip=client_ip)
        await log_action(
            db,
            action="login_failed",
            resource_type="auth",
            details=f"Failed login attempt for {request.email}",
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        logger.warning("login_disabled", email=request.email, ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
        )

    # --- MFA check ---
    if user.mfa_enabled:
        # Return a temporary token; caller must verify MFA before receiving real tokens
        temp_token = create_access_token(
            data={"sub": str(user.id), "purpose": "mfa"},
            expires_delta=timedelta(minutes=5),
        )
        logger.info("mfa_required", user_id=str(user.id), ip=client_ip)
        return MFARequiredResponse(temp_token=temp_token)

    # --- Successful login (no MFA) ---
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(UTC)
    user.last_login_ip = client_ip
    await db.flush()

    tokens = await _issue_tokens(user)

    logger.info(
        "login_success",
        user_id=str(user.id),
        email=user.email,
        role=user.role,
        ip=client_ip,
    )
    await _record_login_attempt(db, request.email, success=True, ip=client_ip)
    await log_action(
        db,
        action="login_success",
        resource_type="auth",
        actor_type="user",
        actor_id=user.id,
        details=f"User {user.email} logged in",
        ip_address=client_ip,
    )

    return TokenResponse(**tokens)


# ---------------------------------------------------------------------------
# POST /verify-mfa
# ---------------------------------------------------------------------------

@router.post("/verify-mfa", response_model=TokenResponse)
async def verify_mfa(
    data: MFAVerifyRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    client_ip = req.client.host if req.client else "unknown"

    # Decode the temporary MFA token
    try:
        from app.core.security import decode_access_token

        payload = decode_access_token(data.temp_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired MFA token",
        ) from None

    if payload.get("purpose") != "mfa":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid MFA token",
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    # Retrieve MFA secret
    mfa_result = await db.execute(
        select(UserMFA).where(UserMFA.user_id == user.id, UserMFA.is_enabled == True)  # noqa: E712
    )
    mfa = mfa_result.scalar_one_or_none()
    if not mfa:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA is not configured for this user",
        )

    if not verify_totp(mfa.totp_secret, data.totp_code):
        logger.warning("mfa_failed", user_id=str(user.id), ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code",
        )

    # MFA passed - issue real tokens
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(UTC)
    user.last_login_ip = client_ip
    await db.flush()

    tokens = await _issue_tokens(user)

    logger.info("mfa_verified", user_id=str(user.id), ip=client_ip)
    await _record_login_attempt(db, user.email, success=True, ip=client_ip)
    await log_action(
        db,
        action="mfa_verified",
        resource_type="auth",
        actor_type="user",
        actor_id=user.id,
        details=f"User {user.email} passed MFA verification",
        ip_address=client_ip,
    )

    return TokenResponse(**tokens)


# ---------------------------------------------------------------------------
# POST /refresh
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = decode_refresh_token(data.refresh_token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from None

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Revoke old refresh token
    await _revoke_token_in_redis(data.refresh_token, ttl_seconds=7 * 24 * 3600)

    # Issue new token pair
    tokens = await _issue_tokens(user)
    return TokenResponse(**tokens)


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------

@router.post("/logout")
async def logout(
    data: LogoutRequest | None = None,
    req: Request = None,
    user: User = Depends(get_current_user),
):
    # Revoke the access token from the Authorization header
    auth_header = req.headers.get("Authorization", "") if req else ""
    if auth_header.startswith("Bearer "):
        access_token = auth_header.removeprefix("Bearer ")
        await _revoke_token_in_redis(access_token)

    # Revoke refresh token if provided
    if data and data.refresh_token:
        await _revoke_token_in_redis(data.refresh_token, ttl_seconds=7 * 24 * 3600)

    logger.info("logout", user_id=str(user.id))
    return {"detail": "Logged out successfully"}


# ---------------------------------------------------------------------------
# POST /change-password
# ---------------------------------------------------------------------------

@router.post("/change-password")
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify current password
    if not verify_password(data.current_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # Validate new password strength
    strength = validate_password_strength(data.new_password)
    if not strength["valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": "Password does not meet requirements", "errors": strength["errors"]},
        )

    # Check password history (prevent reuse of recent passwords)
    history: list = user.password_history if user.password_history else []
    for old_hash in history:
        if verify_password(data.new_password, old_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password must not match any of your recent passwords",
            )

    # Update password
    old_hash = user.hashed_password
    user.hashed_password = hash_password(data.new_password)
    user.password_changed_at = datetime.now(UTC)

    # Append old hash to history (keep last 5)
    history.append(old_hash)
    user.password_history = history[-5:]

    await db.flush()

    logger.info("password_changed", user_id=str(user.id))
    await log_action(
        db,
        action="password_changed",
        resource_type="auth",
        actor_type="user",
        actor_id=user.id,
        details=f"User {user.email} changed their password",
    )

    return {"detail": "Password changed successfully"}


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> User:
    return user
