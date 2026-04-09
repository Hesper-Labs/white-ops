"""Trigger engine - event-driven automation with cron, threshold, and webhook triggers."""

import json
import time
import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trigger import Trigger, TriggerExecution

logger = structlog.get_logger()


class TriggerEngine:
    """Evaluates events against trigger rules and executes matching actions."""

    # ------------------------------------------------------------------
    # Event evaluation
    # ------------------------------------------------------------------

    async def evaluate_event(
        self,
        event_type: str,
        event_data: dict,
        db: AsyncSession,
    ) -> list[dict]:
        """Find and execute all triggers matching the given event."""
        log = logger.bind(event_type=event_type)

        # Find active event-type triggers matching this event
        result = await db.execute(
            select(Trigger).where(
                and_(
                    Trigger.is_active.is_(True),
                    Trigger.is_deleted.is_(False),
                    Trigger.trigger_type == "event",
                )
            )
        )
        triggers = list(result.scalars().all())

        matched = []
        for trigger in triggers:
            config = trigger.config or {}
            # Match on event_type pattern
            trigger_event = config.get("event_type", "")
            if trigger_event and trigger_event != event_type:
                # Support wildcard matching
                if trigger_event.endswith("*"):
                    prefix = trigger_event[:-1]
                    if not event_type.startswith(prefix):
                        continue
                else:
                    continue

            # Check optional filter conditions
            filters = config.get("filters", {})
            if not self._match_filters(filters, event_data):
                continue

            # Execute the trigger
            exec_result = await self.execute_trigger(trigger.id, event_data, db)
            matched.append(exec_result)

        log.info("triggers_evaluated", matched=len(matched), total=len(triggers))
        return matched

    @staticmethod
    def _match_filters(filters: dict, data: dict) -> bool:
        """Check if event data matches all filter conditions."""
        for key, expected in filters.items():
            actual = data.get(key)
            if actual != expected:
                return False
        return True

    # ------------------------------------------------------------------
    # Trigger execution
    # ------------------------------------------------------------------

    async def execute_trigger(
        self,
        trigger_id: uuid.UUID,
        event_data: dict,
        db: AsyncSession,
    ) -> dict:
        """Execute a trigger's action and record the execution."""
        log = logger.bind(trigger_id=str(trigger_id))
        start = time.monotonic()

        result = await db.execute(
            select(Trigger).where(Trigger.id == trigger_id, Trigger.is_deleted.is_(False))
        )
        trigger = result.scalar_one_or_none()
        if not trigger:
            log.warning("trigger_not_found")
            raise ValueError("Trigger not found")

        try:
            action_result = await self._execute_action(
                trigger.action_type, trigger.action_config, event_data, db
            )

            duration_ms = (time.monotonic() - start) * 1000

            # Update trigger metadata
            trigger.last_fired_at = datetime.now(UTC)
            trigger.fire_count += 1
            await db.flush()

            # Record execution
            await self.record_execution(db, trigger_id, "success", action_result, duration_ms)

            log.info("trigger_executed", action_type=trigger.action_type, duration_ms=round(duration_ms, 2))
            return {
                "trigger_id": str(trigger_id),
                "trigger_name": trigger.name,
                "status": "success",
                "action_type": trigger.action_type,
                "result": action_result,
                "duration_ms": round(duration_ms, 2),
            }

        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            await self.record_execution(
                db, trigger_id, "failure", {"error": str(exc)}, duration_ms
            )
            log.error("trigger_execution_failed", error=str(exc))
            return {
                "trigger_id": str(trigger_id),
                "trigger_name": trigger.name,
                "status": "failure",
                "error": str(exc),
                "duration_ms": round(duration_ms, 2),
            }

    async def _execute_action(
        self,
        action_type: str,
        action_config: dict,
        event_data: dict,
        db: AsyncSession,
    ) -> dict:
        """Execute the trigger's action based on its type."""
        if action_type == "create_task":
            return await self._action_create_task(action_config, event_data, db)
        elif action_type == "send_notification":
            return await self._action_send_notification(action_config, event_data, db)
        elif action_type == "execute_workflow":
            return await self._action_execute_workflow(action_config, event_data, db)
        elif action_type == "call_webhook":
            return await self._action_call_webhook(action_config, event_data)
        else:
            raise ValueError(f"Unknown action type: {action_type}")

    async def _action_create_task(self, config: dict, event_data: dict, db: AsyncSession) -> dict:
        """Create a new task as a trigger action."""
        from app.models.task import Task
        from app.services.orchestrator import orchestrator

        task = Task(
            title=config.get("title", "Triggered task"),
            description=config.get("description", ""),
            instructions=config.get("instructions", ""),
            priority=config.get("priority", "medium"),
            metadata_={"trigger_event": event_data},
        )
        db.add(task)
        await db.flush()

        await orchestrator.queue_task(task.id, db)
        return {"task_id": str(task.id), "status": "queued"}

    async def _action_send_notification(self, config: dict, event_data: dict, db: AsyncSession) -> dict:
        """Send a notification as a trigger action."""
        from app.services.notification_service import notification_service

        notification = await notification_service.send(
            db=db,
            channel=config.get("channel", "in_app"),
            subject=config.get("subject", "Trigger fired"),
            body=config.get("body", json.dumps(event_data, default=str)),
            severity=config.get("severity", "info"),
            user_id=uuid.UUID(config["user_id"]) if config.get("user_id") else None,
            metadata=config.get("metadata"),
        )
        return {"notification_id": str(notification.id)}

    async def _action_execute_workflow(self, config: dict, event_data: dict, db: AsyncSession) -> dict:
        """Execute a workflow as a trigger action."""
        from app.services.workflow_engine import workflow_engine

        workflow_id = uuid.UUID(config["workflow_id"])
        result = await workflow_engine.execute_workflow(workflow_id, db, trigger_data=event_data)
        return result

    async def _action_call_webhook(self, config: dict, event_data: dict) -> dict:
        """Call an external webhook as a trigger action."""
        import httpx

        url = config.get("url", "")
        if not url:
            raise ValueError("Webhook URL not configured")

        headers = config.get("headers", {})
        headers.setdefault("Content-Type", "application/json")

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                json=event_data,
                headers=headers,
            )
            return {
                "status_code": response.status_code,
                "response_body": response.text[:500],
            }

    # ------------------------------------------------------------------
    # Trigger creation
    # ------------------------------------------------------------------

    async def create_trigger(
        self,
        db: AsyncSession,
        name: str,
        trigger_type: str,
        config: dict,
        action_type: str,
        action_config: dict,
        created_by: uuid.UUID | None = None,
    ) -> Trigger:
        """Create a new trigger."""
        trigger = Trigger(
            name=name,
            trigger_type=trigger_type,
            config=config,
            action_type=action_type,
            action_config=action_config,
            created_by=created_by,
        )
        db.add(trigger)
        await db.flush()

        logger.info(
            "trigger_created",
            trigger_id=str(trigger.id),
            name=name,
            trigger_type=trigger_type,
            action_type=action_type,
        )
        return trigger

    # ------------------------------------------------------------------
    # Cron triggers
    # ------------------------------------------------------------------

    async def evaluate_cron_triggers(self, db: AsyncSession) -> list[dict]:
        """Check which cron triggers should fire based on their schedule."""
        result = await db.execute(
            select(Trigger).where(
                and_(
                    Trigger.is_active.is_(True),
                    Trigger.is_deleted.is_(False),
                    Trigger.trigger_type == "cron",
                )
            )
        )
        triggers = list(result.scalars().all())
        fired = []

        now = datetime.now(UTC)

        for trigger in triggers:
            config = trigger.config or {}
            cron_expr = config.get("cron_expression", "")
            if not cron_expr:
                continue

            try:
                from croniter import croniter

                cron = croniter(cron_expr, trigger.last_fired_at or trigger.created_at)
                next_fire = cron.get_next(datetime)

                # Make next_fire timezone-aware if it isn't already
                if next_fire.tzinfo is None:
                    next_fire = next_fire.replace(tzinfo=UTC)

                if next_fire <= now:
                    exec_result = await self.execute_trigger(
                        trigger.id, {"cron_expression": cron_expr, "scheduled_time": next_fire.isoformat()}, db
                    )
                    fired.append(exec_result)
            except ImportError:
                logger.warning("trigger_croniter_not_installed", trigger_id=str(trigger.id))
            except Exception as exc:
                logger.error("trigger_cron_eval_failed", trigger_id=str(trigger.id), error=str(exc))

        logger.info("cron_triggers_evaluated", total=len(triggers), fired=len(fired))
        return fired

    # ------------------------------------------------------------------
    # Threshold evaluation
    # ------------------------------------------------------------------

    async def evaluate_threshold(self, trigger: Trigger, current_value: float) -> bool:
        """Evaluate a threshold trigger against a current value."""
        config = trigger.config or {}
        operator = config.get("operator", "gt")
        threshold = config.get("threshold", 0)

        if operator == "gt":
            return current_value > threshold
        elif operator == "gte":
            return current_value >= threshold
        elif operator == "lt":
            return current_value < threshold
        elif operator == "lte":
            return current_value <= threshold
        elif operator == "eq":
            return current_value == threshold
        elif operator == "neq":
            return current_value != threshold
        else:
            logger.warning("trigger_unknown_threshold_operator", operator=operator)
            return False

    # ------------------------------------------------------------------
    # Execution recording and stats
    # ------------------------------------------------------------------

    async def record_execution(
        self,
        db: AsyncSession,
        trigger_id: uuid.UUID,
        status: str,
        result: dict,
        duration_ms: float,
    ) -> TriggerExecution:
        """Record a trigger execution result."""
        execution = TriggerExecution(
            trigger_id=trigger_id,
            status=status,
            result=result,
            error=result.get("error") if status == "failure" else None,
            duration_ms=duration_ms,
            event_data=result,
        )
        db.add(execution)
        await db.flush()
        return execution

    async def get_trigger_stats(self, db: AsyncSession, trigger_id: uuid.UUID) -> dict:
        """Get execution statistics for a trigger."""
        result = await db.execute(
            select(Trigger).where(Trigger.id == trigger_id, Trigger.is_deleted.is_(False))
        )
        trigger = result.scalar_one_or_none()
        if not trigger:
            raise ValueError("Trigger not found")

        # Execution counts by status
        status_result = await db.execute(
            select(TriggerExecution.status, func.count(TriggerExecution.id))
            .where(TriggerExecution.trigger_id == trigger_id)
            .group_by(TriggerExecution.status)
        )
        status_counts = dict(status_result.all())

        # Average duration
        avg_duration_result = await db.execute(
            select(func.avg(TriggerExecution.duration_ms))
            .where(TriggerExecution.trigger_id == trigger_id)
        )
        avg_duration = float(avg_duration_result.scalar() or 0)

        # Last 5 executions
        recent_result = await db.execute(
            select(TriggerExecution)
            .where(TriggerExecution.trigger_id == trigger_id)
            .order_by(TriggerExecution.created_at.desc())
            .limit(5)
        )
        recent = [
            {
                "id": str(e.id),
                "status": e.status,
                "duration_ms": round(e.duration_ms, 2),
                "created_at": e.created_at.isoformat(),
                "error": e.error,
            }
            for e in recent_result.scalars().all()
        ]

        total_executions = sum(status_counts.values())
        success_count = status_counts.get("success", 0)
        success_rate = (success_count / total_executions * 100) if total_executions > 0 else 0

        return {
            "trigger_id": str(trigger_id),
            "name": trigger.name,
            "trigger_type": trigger.trigger_type,
            "is_active": trigger.is_active,
            "fire_count": trigger.fire_count,
            "last_fired_at": trigger.last_fired_at.isoformat() if trigger.last_fired_at else None,
            "execution_counts": status_counts,
            "total_executions": total_executions,
            "success_rate": round(success_rate, 2),
            "avg_duration_ms": round(avg_duration, 2),
            "recent_executions": recent,
        }


trigger_engine = TriggerEngine()
