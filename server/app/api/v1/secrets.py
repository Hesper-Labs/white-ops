"""Secrets Vault API - encrypted secret storage with audit logging."""

import uuid
from datetime import datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.services.vault import vault_service

logger = structlog.get_logger()
router = APIRouter()


@router.get("/")
async def list_secrets(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    category: str | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List secrets metadata (no decrypted values)."""
    all_secrets = await vault_service.list_secrets(db, category=category)
    total = len(all_secrets)
    items = all_secrets[skip : skip + limit]
    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_secret(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("secrets:write")),
) -> dict:
    """Create a new encrypted secret."""
    name = data.get("name")
    value = data.get("value")
    category = data.get("category", "general")

    if not name or not value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'name' and 'value' are required",
        )

    expires_at = None
    if data.get("expires_at"):
        expires_at = datetime.fromisoformat(data["expires_at"])

    try:
        secret = await vault_service.store_secret(
            db=db,
            name=name,
            value=value,
            category=category,
            description=data.get("description"),
            created_by=user.id,
            expires_at=expires_at,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    logger.info("secret_created", secret_id=str(secret.id), name=name, user_id=str(user.id))
    return {
        "id": str(secret.id),
        "name": secret.name,
        "category": secret.category,
        "version": secret.version,
        "created_at": secret.created_at.isoformat(),
    }


@router.get("/{secret_id}")
async def get_secret(
    secret_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("secrets:read")),
) -> dict:
    """Get a secret value (decrypted). Access is audit-logged."""
    try:
        result = await vault_service.get_secret(db, secret_id, audit_user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    logger.info("secret_accessed", secret_id=str(secret_id), user_id=str(user.id))
    return result


@router.put("/{secret_id}")
async def update_secret(
    secret_id: uuid.UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("secrets:write")),
) -> dict:
    """Update/rotate a secret value."""
    new_value = data.get("value")
    if not new_value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'value' is required for rotation",
        )

    try:
        secret = await vault_service.rotate_secret(
            db=db,
            secret_id=secret_id,
            new_value=new_value,
            rotated_by=user.id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    logger.info("secret_rotated", secret_id=str(secret_id), version=secret.version)
    return {
        "id": str(secret.id),
        "name": secret.name,
        "version": secret.version,
        "rotated_at": secret.rotated_at.isoformat() if secret.rotated_at else None,
    }


@router.delete("/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(
    secret_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_permission("secrets:write")),
) -> None:
    """Soft-delete a secret."""
    deleted = await vault_service.delete_secret(db, secret_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")

    logger.info("secret_deleted", secret_id=str(secret_id), user_id=str(user.id))
