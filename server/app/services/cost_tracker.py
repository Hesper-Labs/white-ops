"""Cost tracking service - record LLM usage, compute costs, budget management, and forecasting."""

import uuid
from datetime import datetime, timezone, timedelta

import structlog
from sqlalchemy import select, func, and_, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cost import CostRecord, Budget

logger = structlog.get_logger()


class CostTracker:
    """Tracks LLM API usage costs with budgeting, forecasting, and alerting."""

    # Token pricing per provider/model (approximate USD per 1K tokens)
    PRICING: dict[str, dict[str, dict[str, float]]] = {
        "anthropic": {
            "claude-opus-4-20250514": {"input": 0.015, "output": 0.075},
            "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
            "claude-3-5-haiku-20241022": {"input": 0.001, "output": 0.005},
        },
        "openai": {
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        },
    }

    def _calculate_cost(self, provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD based on token counts and pricing table."""
        provider_pricing = self.PRICING.get(provider, {})
        model_pricing = provider_pricing.get(model, {})

        if not model_pricing:
            # Fallback: try partial model name match
            for model_name, pricing in provider_pricing.items():
                if model_name in model or model in model_name:
                    model_pricing = pricing
                    break

        if not model_pricing:
            logger.warning("cost_tracker_no_pricing", provider=provider, model=model)
            return 0.0

        input_cost = (input_tokens / 1000.0) * model_pricing.get("input", 0)
        output_cost = (output_tokens / 1000.0) * model_pricing.get("output", 0)
        return round(input_cost + output_cost, 6)

    # ------------------------------------------------------------------
    # Record usage
    # ------------------------------------------------------------------

    async def record_usage(
        self,
        db: AsyncSession,
        agent_id: uuid.UUID | None,
        task_id: uuid.UUID | None,
        provider: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> CostRecord:
        """Record a token usage event and compute cost."""
        cost = self._calculate_cost(provider, model, input_tokens, output_tokens)

        record = CostRecord(
            agent_id=agent_id,
            task_id=task_id,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )
        db.add(record)
        await db.flush()

        logger.info(
            "cost_recorded",
            agent_id=str(agent_id) if agent_id else None,
            provider=provider,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )

        # Check budget alerts
        await self._check_budget_alerts(db, cost)

        return record

    async def _check_budget_alerts(self, db: AsyncSession, new_cost: float) -> None:
        """Check if spending has crossed any budget thresholds."""
        budget_status = await self.get_budget_status(db)
        if not budget_status.get("has_budget"):
            return

        pct = budget_status.get("percent_used", 0)
        thresholds = budget_status.get("alert_thresholds", [])

        for threshold in thresholds:
            if pct >= threshold:
                logger.warning(
                    "cost_budget_threshold_reached",
                    threshold_pct=threshold,
                    current_pct=round(pct, 1),
                    monthly_limit=budget_status.get("monthly_limit"),
                    current_spend=budget_status.get("current_spend"),
                )

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    async def get_daily_costs(
        self,
        db: AsyncSession,
        days: int = 30,
    ) -> list[dict]:
        """Get daily cost breakdown for the last N days."""
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await db.execute(
            select(
                cast(CostRecord.created_at, Date).label("date"),
                CostRecord.provider,
                func.sum(CostRecord.cost_usd).label("total_cost"),
                func.sum(CostRecord.input_tokens).label("total_input"),
                func.sum(CostRecord.output_tokens).label("total_output"),
                func.count(CostRecord.id).label("request_count"),
            )
            .where(CostRecord.created_at >= since)
            .group_by(cast(CostRecord.created_at, Date), CostRecord.provider)
            .order_by(cast(CostRecord.created_at, Date).desc())
        )
        rows = result.all()

        # Group by date
        daily: dict[str, dict] = {}
        for row in rows:
            date_str = str(row.date)
            if date_str not in daily:
                daily[date_str] = {"date": date_str, "total_cost": 0.0, "by_provider": {}, "request_count": 0}
            daily[date_str]["total_cost"] += float(row.total_cost or 0)
            daily[date_str]["request_count"] += int(row.request_count or 0)
            daily[date_str]["by_provider"][row.provider] = {
                "cost": float(row.total_cost or 0),
                "input_tokens": int(row.total_input or 0),
                "output_tokens": int(row.total_output or 0),
            }

        return sorted(daily.values(), key=lambda d: d["date"], reverse=True)

    async def get_agent_costs(
        self,
        db: AsyncSession,
        agent_id: uuid.UUID | None = None,
        period_days: int = 30,
    ) -> list[dict]:
        """Get cost breakdown by agent."""
        since = datetime.now(timezone.utc) - timedelta(days=period_days)

        query = (
            select(
                CostRecord.agent_id,
                func.sum(CostRecord.cost_usd).label("total_cost"),
                func.sum(CostRecord.input_tokens).label("total_input"),
                func.sum(CostRecord.output_tokens).label("total_output"),
                func.count(CostRecord.id).label("request_count"),
            )
            .where(CostRecord.created_at >= since)
        )

        if agent_id:
            query = query.where(CostRecord.agent_id == agent_id)

        query = query.group_by(CostRecord.agent_id).order_by(func.sum(CostRecord.cost_usd).desc())

        result = await db.execute(query)
        return [
            {
                "agent_id": str(row.agent_id) if row.agent_id else None,
                "total_cost": round(float(row.total_cost or 0), 6),
                "total_input_tokens": int(row.total_input or 0),
                "total_output_tokens": int(row.total_output or 0),
                "request_count": int(row.request_count or 0),
            }
            for row in result.all()
        ]

    # ------------------------------------------------------------------
    # Budget management
    # ------------------------------------------------------------------

    async def get_budget_status(self, db: AsyncSession) -> dict:
        """Get current monthly spend vs budget."""
        # Find active budget
        result = await db.execute(
            select(Budget).where(Budget.is_active.is_(True), Budget.is_deleted.is_(False)).limit(1)
        )
        budget = result.scalar_one_or_none()

        # Calculate current month's spending
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        spend_result = await db.execute(
            select(func.sum(CostRecord.cost_usd)).where(CostRecord.created_at >= month_start)
        )
        current_spend = float(spend_result.scalar() or 0)

        if not budget:
            return {
                "has_budget": False,
                "current_spend": round(current_spend, 4),
                "month_start": month_start.isoformat(),
            }

        monthly_limit = budget.monthly_limit_usd
        percent_used = (current_spend / monthly_limit * 100) if monthly_limit > 0 else 0

        return {
            "has_budget": True,
            "monthly_limit": monthly_limit,
            "current_spend": round(current_spend, 4),
            "remaining": round(monthly_limit - current_spend, 4),
            "percent_used": round(percent_used, 2),
            "alert_thresholds": budget.alert_thresholds or [],
            "is_over_budget": current_spend >= monthly_limit,
            "month_start": month_start.isoformat(),
        }

    async def set_budget(
        self,
        db: AsyncSession,
        monthly_limit: float,
        alert_thresholds: list[int] | None = None,
    ) -> Budget:
        """Set or update the active monthly budget."""
        if alert_thresholds is None:
            alert_thresholds = [80, 90, 100]

        # Deactivate existing budgets
        existing_result = await db.execute(
            select(Budget).where(Budget.is_active.is_(True), Budget.is_deleted.is_(False))
        )
        for existing in existing_result.scalars().all():
            existing.is_active = False

        budget = Budget(
            monthly_limit_usd=monthly_limit,
            alert_thresholds=alert_thresholds,
            is_active=True,
        )
        db.add(budget)
        await db.flush()

        logger.info("cost_budget_set", monthly_limit=monthly_limit, thresholds=alert_thresholds)
        return budget

    # ------------------------------------------------------------------
    # Forecasting
    # ------------------------------------------------------------------

    async def get_cost_forecast(self, db: AsyncSession, days: int = 30) -> dict:
        """Predict future costs based on recent daily averages."""
        now = datetime.now(timezone.utc)
        since = now - timedelta(days=days)

        # Daily cost averages
        result = await db.execute(
            select(
                cast(CostRecord.created_at, Date).label("date"),
                func.sum(CostRecord.cost_usd).label("daily_cost"),
            )
            .where(CostRecord.created_at >= since)
            .group_by(cast(CostRecord.created_at, Date))
        )
        daily_costs = [float(row.daily_cost or 0) for row in result.all()]

        if not daily_costs:
            return {
                "avg_daily_cost": 0,
                "projected_monthly_cost": 0,
                "data_points": 0,
                "period_days": days,
            }

        avg_daily = sum(daily_costs) / len(daily_costs)

        # Days remaining in month
        days_in_month = 30  # approximation
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        days_elapsed = (now - month_start).days + 1
        days_remaining = max(days_in_month - days_elapsed, 0)

        # Current month's actual spend
        spend_result = await db.execute(
            select(func.sum(CostRecord.cost_usd)).where(CostRecord.created_at >= month_start)
        )
        current_spend = float(spend_result.scalar() or 0)

        projected = current_spend + (avg_daily * days_remaining)

        return {
            "avg_daily_cost": round(avg_daily, 4),
            "projected_monthly_cost": round(projected, 4),
            "current_month_spend": round(current_spend, 4),
            "days_remaining": days_remaining,
            "data_points": len(daily_costs),
            "period_days": days,
            "trend": "increasing" if len(daily_costs) > 1 and daily_costs[-1] > daily_costs[0] else "stable",
        }

    # ------------------------------------------------------------------
    # Provider breakdown
    # ------------------------------------------------------------------

    async def get_provider_breakdown(
        self,
        db: AsyncSession,
        period_days: int = 30,
    ) -> list[dict]:
        """Get cost breakdown by provider and model."""
        since = datetime.now(timezone.utc) - timedelta(days=period_days)

        result = await db.execute(
            select(
                CostRecord.provider,
                CostRecord.model,
                func.sum(CostRecord.cost_usd).label("total_cost"),
                func.sum(CostRecord.input_tokens).label("total_input"),
                func.sum(CostRecord.output_tokens).label("total_output"),
                func.count(CostRecord.id).label("request_count"),
            )
            .where(CostRecord.created_at >= since)
            .group_by(CostRecord.provider, CostRecord.model)
            .order_by(func.sum(CostRecord.cost_usd).desc())
        )

        return [
            {
                "provider": row.provider,
                "model": row.model,
                "total_cost": round(float(row.total_cost or 0), 6),
                "total_input_tokens": int(row.total_input or 0),
                "total_output_tokens": int(row.total_output or 0),
                "request_count": int(row.request_count or 0),
                "avg_cost_per_request": round(
                    float(row.total_cost or 0) / max(int(row.request_count or 1), 1), 6
                ),
            }
            for row in result.all()
        ]


cost_tracker = CostTracker()
