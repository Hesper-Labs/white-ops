"""Cost Management API - track spending, budgets, and forecasts."""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user, require_admin
from app.db.session import get_db
from app.models.user import User
from app.services.cost_tracker import cost_tracker

logger = structlog.get_logger()
router = APIRouter()


@router.get("/summary")
async def get_cost_summary(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Get cost summary including total spend, daily average, and budget status."""
    budget_status = await cost_tracker.get_budget_status(db)
    daily_costs = await cost_tracker.get_daily_costs(db, days=30)

    total_30d = sum(d.get("total_cost", 0) for d in daily_costs)
    daily_avg = total_30d / max(len(daily_costs), 1)

    return {
        "total_30_days": round(total_30d, 4),
        "daily_average": round(daily_avg, 4),
        "budget": budget_status,
        "days_with_data": len(daily_costs),
    }


@router.get("/daily")
async def get_daily_costs(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365),
) -> dict:
    """Get daily cost breakdown for the last N days."""
    daily = await cost_tracker.get_daily_costs(db, days=days)
    return {"items": daily, "days": days, "total": len(daily)}


@router.get("/by-agent")
async def get_costs_by_agent(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365),
) -> dict:
    """Get cost breakdown per agent."""
    agent_costs = await cost_tracker.get_agent_costs(db, period_days=days)
    return {"items": agent_costs, "period_days": days, "total": len(agent_costs)}


@router.get("/by-provider")
async def get_costs_by_provider(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365),
) -> dict:
    """Get cost breakdown per LLM provider and model."""
    provider_costs = await cost_tracker.get_provider_breakdown(db, period_days=days)
    return {"items": provider_costs, "period_days": days, "total": len(provider_costs)}


@router.get("/budget")
async def get_budget(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    """Get current budget configuration and status."""
    return await cost_tracker.get_budget_status(db)


@router.put("/budget")
async def set_budget(
    data: dict,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
) -> dict:
    """Set or update monthly budget limits."""
    monthly_limit = data.get("monthly_limit_usd")
    if monthly_limit is None or monthly_limit < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'monthly_limit_usd' is required and must be non-negative",
        )

    budget = await cost_tracker.set_budget(
        db=db,
        monthly_limit=monthly_limit,
        alert_thresholds=data.get("alert_thresholds"),
    )

    logger.info(
        "budget_updated",
        monthly_limit=monthly_limit,
        user_id=str(user.id),
    )

    return {
        "id": str(budget.id),
        "monthly_limit_usd": budget.monthly_limit_usd,
        "alert_thresholds": budget.alert_thresholds,
        "is_active": budget.is_active,
        "created_at": budget.created_at.isoformat(),
    }


@router.get("/forecast")
async def get_cost_forecast(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    days: int = Query(30, ge=7, le=90),
) -> dict:
    """Get cost forecast based on recent spending patterns."""
    forecast = await cost_tracker.get_cost_forecast(db, days=days)
    return forecast
