"""Webhook Management API - manage webhook endpoints and delivery history."""

import uuid
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_operator
from app.db.session import get_db
from app.models.webhook import WebhookEndpoint
from app.models.user import User
from app.services.audit import log_action

logger = structlog.get_logger()
router = APIRouter()

# In-memory delivery history (in production, use a dedicated DB model)
_delivery_history: dict[str, list[dict]] = {}


@router.get("/")
async def list_webhooks(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List all webhook endpoints."""
    count_result = await db.execute(
        select(func.count(WebhookEndpoint.id)).where(WebhookEndpoint.is_deleted.is_(False))
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(WebhookEndpoint)
        .where(WebhookEndpoint.is_deleted.is_(False))
        .order_by(WebhookEndpoint.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    webhooks = result.scalars().all()

    items = [
        {
            "id": str(w.id),
            "name": w.name,
            "url": w.url,
            "events": w.events,
            "is_active": w.is_active,
            "headers": w.headers,
            "retry_policy": w.retry_policy,
            "last_triggered_at": w.last_triggered_at.isoformat() if w.last_triggered_at else None,
            "failure_count": w.failure_count,
            "created_at": w.created_at.isoformat(),
        }
        for w in webhooks
    ]

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_webhook(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Create a new webhook endpoint."""
    name = data.get("name")
    url = data.get("url")

    if not name or not url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'name' and 'url' are required",
        )

    webhook = WebhookEndpoint(
        name=name,
        url=url,
        secret=data.get("secret"),
        events=data.get("events", []),
        is_active=data.get("is_active", True),
        headers=data.get("headers", {}),
        retry_policy=data.get("retry_policy", {"max_retries": 3, "backoff_seconds": 60}),
        created_by=user.id,
    )
    db.add(webhook)
    await db.flush()

    await log_action(
        db,
        action="webhook_created",
        resource_type="webhook",
        resource_id=webhook.id,
        actor_type="user",
        actor_id=user.id,
        details=f"Webhook '{name}' created for {url}",
    )
    logger.info("webhook_created", webhook_id=str(webhook.id), url=url)

    return {
        "id": str(webhook.id),
        "name": webhook.name,
        "url": webhook.url,
        "events": webhook.events,
        "is_active": webhook.is_active,
        "created_at": webhook.created_at.isoformat(),
    }


@router.get("/{webhook_id}")
async def get_webhook(
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Get webhook endpoint detail."""
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == webhook_id,
            WebhookEndpoint.is_deleted.is_(False),
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    return {
        "id": str(webhook.id),
        "name": webhook.name,
        "url": webhook.url,
        "secret": "***" if webhook.secret else None,
        "events": webhook.events,
        "is_active": webhook.is_active,
        "headers": webhook.headers,
        "retry_policy": webhook.retry_policy,
        "last_triggered_at": webhook.last_triggered_at.isoformat() if webhook.last_triggered_at else None,
        "failure_count": webhook.failure_count,
        "created_by": str(webhook.created_by) if webhook.created_by else None,
        "created_at": webhook.created_at.isoformat(),
        "updated_at": webhook.updated_at.isoformat(),
    }


@router.put("/{webhook_id}")
async def update_webhook(
    webhook_id: uuid.UUID,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Update a webhook endpoint."""
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == webhook_id,
            WebhookEndpoint.is_deleted.is_(False),
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    updatable = ["name", "url", "secret", "events", "is_active", "headers", "retry_policy"]
    for field in updatable:
        if field in data:
            setattr(webhook, field, data[field])

    await db.flush()

    await log_action(
        db,
        action="webhook_updated",
        resource_type="webhook",
        resource_id=webhook_id,
        actor_type="user",
        actor_id=user.id,
        details=f"Webhook '{webhook.name}' updated",
    )
    logger.info("webhook_updated", webhook_id=str(webhook_id))

    return {
        "id": str(webhook.id),
        "name": webhook.name,
        "url": webhook.url,
        "events": webhook.events,
        "is_active": webhook.is_active,
        "updated_at": webhook.updated_at.isoformat(),
    }


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> None:
    """Soft-delete a webhook endpoint."""
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == webhook_id,
            WebhookEndpoint.is_deleted.is_(False),
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    webhook.soft_delete()
    await db.flush()

    await log_action(
        db,
        action="webhook_deleted",
        resource_type="webhook",
        resource_id=webhook_id,
        actor_type="user",
        actor_id=user.id,
        details=f"Webhook '{webhook.name}' deleted",
    )
    logger.info("webhook_deleted", webhook_id=str(webhook_id))


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Send a test payload to the webhook endpoint."""
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == webhook_id,
            WebhookEndpoint.is_deleted.is_(False),
        )
    )
    webhook = result.scalar_one_or_none()
    if not webhook:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    test_payload = {
        "event": "test",
        "webhook_id": str(webhook_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": "This is a test payload from White-Ops",
    }

    try:
        import httpx

        headers = dict(webhook.headers or {})
        headers.setdefault("Content-Type", "application/json")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                webhook.url,
                json=test_payload,
                headers=headers,
            )

        delivery = {
            "id": str(uuid.uuid4()),
            "event": "test",
            "status_code": response.status_code,
            "success": response.status_code < 400,
            "response_body": response.text[:500],
            "delivered_at": datetime.now(timezone.utc).isoformat(),
        }

        # Record in delivery history
        wid = str(webhook_id)
        if wid not in _delivery_history:
            _delivery_history[wid] = []
        _delivery_history[wid].append(delivery)

        webhook.last_triggered_at = datetime.now(timezone.utc)
        await db.flush()

        logger.info("webhook_test_sent", webhook_id=str(webhook_id), status_code=response.status_code)
        return {"status": "delivered", "delivery": delivery}

    except Exception as exc:
        logger.error("webhook_test_failed", webhook_id=str(webhook_id), error=str(exc))
        webhook.failure_count += 1
        await db.flush()
        return {"status": "failed", "error": str(exc)}


@router.get("/{webhook_id}/deliveries")
async def get_deliveries(
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """Get recent delivery history for a webhook."""
    # Verify webhook exists
    result = await db.execute(
        select(WebhookEndpoint).where(
            WebhookEndpoint.id == webhook_id,
            WebhookEndpoint.is_deleted.is_(False),
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")

    deliveries = _delivery_history.get(str(webhook_id), [])
    deliveries.sort(key=lambda x: x.get("delivered_at", ""), reverse=True)
    total = len(deliveries)
    paged = deliveries[skip : skip + limit]

    return {"items": paged, "total": total, "skip": skip, "limit": limit}
