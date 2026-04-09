"""Approval Workflow API - manage approval requests and rules."""

import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_admin, require_operator
from app.db.session import get_db
from app.models.user import User
from app.services.audit import log_action

logger = structlog.get_logger()
router = APIRouter()

# In-memory stores (in production, use dedicated DB models)
_approval_requests: dict[str, dict] = {}
_approval_rules: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Approval requests
# ---------------------------------------------------------------------------

@router.get("/")
async def list_approvals(
    user: User = Depends(get_current_user),
    status_filter: str | None = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List approval requests with optional status filter."""
    items = list(_approval_requests.values())

    if status_filter:
        items = [a for a in items if a.get("status") == status_filter]

    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    total = len(items)
    paged = items[skip : skip + limit]
    return {"items": paged, "total": total, "skip": skip, "limit": limit}


@router.get("/rules")
async def list_approval_rules(
    user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """List approval rules."""
    items = list(_approval_rules.values())
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    total = len(items)
    paged = items[skip : skip + limit]
    return {"items": paged, "total": total, "skip": skip, "limit": limit}


@router.post("/rules", status_code=status.HTTP_201_CREATED)
async def create_approval_rule(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Create an approval rule."""
    rule_id = str(uuid.uuid4())
    rule = {
        "id": rule_id,
        "name": data.get("name", ""),
        "resource_type": data.get("resource_type", ""),
        "action": data.get("action", ""),
        "conditions": data.get("conditions", {}),
        "approvers": data.get("approvers", []),
        "min_approvals": data.get("min_approvals", 1),
        "auto_approve_after_hours": data.get("auto_approve_after_hours"),
        "is_active": True,
        "created_by": str(user.id),
        "created_at": datetime.now(UTC).isoformat(),
    }
    _approval_rules[rule_id] = rule

    await log_action(
        db,
        action="approval_rule_created",
        resource_type="approval_rule",
        resource_id=rule_id,
        actor_type="user",
        actor_id=user.id,
        details=f"Approval rule '{rule['name']}' created",
    )
    logger.info("approval_rule_created", rule_id=rule_id, name=rule["name"])
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_approval_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> None:
    """Delete an approval rule."""
    if rule_id not in _approval_rules:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval rule not found")

    rule = _approval_rules.pop(rule_id)
    await log_action(
        db,
        action="approval_rule_deleted",
        resource_type="approval_rule",
        resource_id=rule_id,
        actor_type="user",
        actor_id=user.id,
        details=f"Approval rule '{rule['name']}' deleted",
    )
    logger.info("approval_rule_deleted", rule_id=rule_id)


@router.get("/{approval_id}")
async def get_approval(
    approval_id: str,
    user: User = Depends(get_current_user),
) -> dict:
    """Get approval request detail."""
    approval = _approval_requests.get(approval_id)
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")
    return approval


@router.post("/{approval_id}/approve")
async def approve_request(
    approval_id: str,
    data: dict | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Approve a pending request."""
    approval = _approval_requests.get(approval_id)
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")

    if approval["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve request with status '{approval['status']}'",
        )

    approval["status"] = "approved"
    approval["decided_by"] = str(user.id)
    approval["decided_at"] = datetime.now(UTC).isoformat()
    approval["decision_note"] = (data or {}).get("note", "")

    await log_action(
        db,
        action="approval_approved",
        resource_type="approval",
        resource_id=approval_id,
        actor_type="user",
        actor_id=user.id,
        details=f"Approval request '{approval_id}' approved",
    )
    logger.info("approval_approved", approval_id=approval_id, user_id=str(user.id))
    return approval


@router.post("/{approval_id}/reject")
async def reject_request(
    approval_id: str,
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_operator),
) -> dict:
    """Reject a pending request with a reason."""
    approval = _approval_requests.get(approval_id)
    if not approval:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found")

    if approval["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject request with status '{approval['status']}'",
        )

    reason = data.get("reason", "")
    if not reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A reason is required when rejecting",
        )

    approval["status"] = "rejected"
    approval["decided_by"] = str(user.id)
    approval["decided_at"] = datetime.now(UTC).isoformat()
    approval["rejection_reason"] = reason

    await log_action(
        db,
        action="approval_rejected",
        resource_type="approval",
        resource_id=approval_id,
        actor_type="user",
        actor_id=user.id,
        details=f"Approval request '{approval_id}' rejected: {reason}",
    )
    logger.info("approval_rejected", approval_id=approval_id, user_id=str(user.id))
    return approval
