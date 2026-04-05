import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.security import verify_password, create_access_token
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.audit import log_action

logger = structlog.get_logger()
router = APIRouter()


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    client_ip = req.client.host if req.client else "unknown"

    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.hashed_password):
        logger.warning("login_failed", email=request.email, ip=client_ip)
        await log_action(
            db, action="login_failed", resource_type="auth",
            details=f"Failed login attempt for {request.email}",
            ip_address=client_ip,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    if not user.is_active:
        logger.warning("login_disabled", email=request.email, ip=client_ip)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
        )

    access_token = create_access_token(data={"sub": str(user.id), "role": user.role})

    logger.info("login_success", user_id=str(user.id), email=user.email, role=user.role, ip=client_ip)
    await log_action(
        db, action="login_success", resource_type="auth",
        actor_type="user", actor_id=user.id,
        details=f"User {user.email} logged in",
        ip_address=client_ip,
    )

    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> User:
    return user
