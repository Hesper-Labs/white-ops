"""DAG-based workflow execution engine with parallel step execution and recovery."""

import asyncio
import json
import time
import uuid
from collections import defaultdict, deque
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.workflow import Workflow, WorkflowStep

logger = structlog.get_logger()


class WorkflowEngine:
    """Executes DAG-based workflows with dependency resolution, parallel execution,
    conditional branching, retry policies, and Redis-backed state persistence."""

    def __init__(self):
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=0,
                decode_responses=True,
            )
        return self._redis

    # ------------------------------------------------------------------
    # State persistence helpers
    # ------------------------------------------------------------------

    def _state_key(self, workflow_id: uuid.UUID) -> str:
        return f"whiteops:workflow:{workflow_id}:state"

    def _step_key(self, workflow_id: uuid.UUID, step_id: uuid.UUID) -> str:
        return f"whiteops:workflow:{workflow_id}:step:{step_id}"

    async def _save_state(self, workflow_id: uuid.UUID, state: dict) -> None:
        r = await self._get_redis()
        await r.set(self._state_key(workflow_id), json.dumps(state, default=str), ex=86400)

    async def _load_state(self, workflow_id: uuid.UUID) -> dict | None:
        r = await self._get_redis()
        raw = await r.get(self._state_key(workflow_id))
        return json.loads(raw) if raw else None

    async def _emit_event(self, event_type: str, data: dict) -> None:
        r = await self._get_redis()
        await r.publish("whiteops:events:workflow", json.dumps({
            "event": event_type,
            **data,
            "timestamp": datetime.now(UTC).isoformat(),
        }, default=str))

    # ------------------------------------------------------------------
    # Topological sort
    # ------------------------------------------------------------------

    @staticmethod
    def _topological_sort(steps: list[WorkflowStep]) -> list[list[WorkflowStep]]:
        """Return steps grouped into layers for parallel execution.

        Each layer contains steps whose dependencies are all in previous layers.
        """
        id_to_step = {step.id: step for step in steps}
        in_degree: dict[uuid.UUID, int] = {step.id: 0 for step in steps}
        dependents: dict[uuid.UUID, list[uuid.UUID]] = defaultdict(list)

        for step in steps:
            deps = step.depends_on or []
            for dep_id_str in deps:
                dep_id = uuid.UUID(str(dep_id_str))
                if dep_id in id_to_step:
                    in_degree[step.id] += 1
                    dependents[dep_id].append(step.id)

        # BFS layer-by-layer
        queue = deque([sid for sid, deg in in_degree.items() if deg == 0])
        layers: list[list[WorkflowStep]] = []

        while queue:
            layer = []
            next_queue: deque[uuid.UUID] = deque()
            for sid in queue:
                layer.append(id_to_step[sid])
            for step in layer:
                for dep_sid in dependents.get(step.id, []):
                    in_degree[dep_sid] -= 1
                    if in_degree[dep_sid] == 0:
                        next_queue.append(dep_sid)
            layers.append(layer)
            queue = next_queue

        # Detect cycles
        total_sorted = sum(len(layer) for layer in layers)
        if total_sorted < len(steps):
            raise ValueError("Workflow contains a dependency cycle")

        return layers

    # ------------------------------------------------------------------
    # Condition evaluation
    # ------------------------------------------------------------------

    async def evaluate_condition(self, condition: dict, context: dict) -> bool:
        """Evaluate a simple condition against the workflow context.

        Supported operators: eq, neq, gt, lt, gte, lte, contains, in, exists.
        """
        field = condition.get("field", "")
        operator = condition.get("operator", "eq")
        expected = condition.get("value")

        # Navigate dotted field paths in context
        actual = context
        for part in field.split("."):
            if isinstance(actual, dict):
                actual = actual.get(part)
            else:
                actual = None
                break

        if operator == "exists":
            return actual is not None
        if operator == "eq":
            return actual == expected
        if operator == "neq":
            return actual != expected
        if operator == "gt":
            return actual is not None and actual > expected
        if operator == "lt":
            return actual is not None and actual < expected
        if operator == "gte":
            return actual is not None and actual >= expected
        if operator == "lte":
            return actual is not None and actual <= expected
        if operator == "contains":
            return expected in actual if actual else False
        if operator == "in":
            return actual in expected if expected else False

        logger.warning("workflow_unknown_operator", operator=operator)
        return False

    # ------------------------------------------------------------------
    # Step execution
    # ------------------------------------------------------------------

    async def execute_step(
        self,
        step: WorkflowStep,
        context: dict,
        db: AsyncSession,
    ) -> dict:
        """Execute a single workflow step and return its output."""
        log = logger.bind(step_id=str(step.id), step_name=step.name, step_type=step.step_type)
        start = time.monotonic()

        try:
            # Check condition if present
            condition = (step.config or {}).get("condition")
            if condition:
                should_run = await self.evaluate_condition(condition, context)
                if not should_run:
                    log.info("workflow_step_skipped", reason="condition_not_met")
                    step.status = "skipped"
                    await db.flush()
                    return {"status": "skipped", "reason": "condition_not_met"}

            step.status = "running"
            await db.flush()

            await self._emit_event("step_started", {
                "workflow_id": str(step.workflow_id),
                "step_id": str(step.id),
                "step_name": step.name,
            })

            result: dict = {}

            if step.step_type == "task":
                # Create a task via the orchestrator
                result = await self._execute_task_step(step, context, db)
            elif step.step_type == "condition":
                # Evaluate and store the boolean result
                cond = (step.config or {}).get("condition", {})
                result = {"result": await self.evaluate_condition(cond, context)}
            elif step.step_type == "notify":
                result = await self._execute_notify_step(step, context, db)
            elif step.step_type == "wait":
                wait_seconds = (step.config or {}).get("wait_seconds", 0)
                await asyncio.sleep(min(wait_seconds, 300))  # cap at 5 min
                result = {"waited_seconds": wait_seconds}
            elif step.step_type == "parallel":
                # Parallel is handled at the layer level; individual step is a no-op marker
                result = {"status": "parallel_marker"}
            else:
                log.warning("workflow_unknown_step_type")
                result = {"status": "unknown_type", "step_type": step.step_type}

            elapsed_ms = (time.monotonic() - start) * 1000
            step.status = "completed"
            await db.flush()

            await self._emit_event("step_completed", {
                "workflow_id": str(step.workflow_id),
                "step_id": str(step.id),
                "step_name": step.name,
                "duration_ms": round(elapsed_ms, 2),
            })

            log.info("workflow_step_completed", duration_ms=round(elapsed_ms, 2))
            return {"status": "completed", "output": result, "duration_ms": round(elapsed_ms, 2)}

        except Exception as exc:
            elapsed_ms = (time.monotonic() - start) * 1000
            step.status = "failed"
            await db.flush()

            await self._emit_event("step_failed", {
                "workflow_id": str(step.workflow_id),
                "step_id": str(step.id),
                "step_name": step.name,
                "error": str(exc),
            })

            log.error("workflow_step_failed", error=str(exc), duration_ms=round(elapsed_ms, 2))
            return {"status": "failed", "error": str(exc), "duration_ms": round(elapsed_ms, 2)}

    async def _execute_task_step(self, step: WorkflowStep, context: dict, db: AsyncSession) -> dict:
        """Create and queue a task for a workflow step."""
        from app.models.task import Task
        from app.services.orchestrator import orchestrator

        config = step.config or {}
        task = Task(
            title=config.get("title", step.name),
            description=config.get("description", ""),
            instructions=config.get("instructions", ""),
            priority=config.get("priority", "medium"),
            workflow_id=step.workflow_id,
            agent_id=step.agent_id,
        )
        db.add(task)
        await db.flush()

        await orchestrator.queue_task(task.id, db)
        return {"task_id": str(task.id), "status": "queued"}

    async def _execute_notify_step(self, step: WorkflowStep, context: dict, db: AsyncSession) -> dict:
        """Send a notification as part of a workflow step."""
        config = step.config or {}
        # Inline notification creation to avoid circular imports
        from app.models.notification import Notification

        notification = Notification(
            channel=config.get("channel", "in_app"),
            subject=config.get("subject", f"Workflow step: {step.name}"),
            body=config.get("body", ""),
            severity=config.get("severity", "info"),
            user_id=uuid.UUID(config["user_id"]) if config.get("user_id") else None,
        )
        db.add(notification)
        await db.flush()
        return {"notification_id": str(notification.id)}

    # ------------------------------------------------------------------
    # Workflow execution
    # ------------------------------------------------------------------

    async def execute_workflow(
        self,
        workflow_id: uuid.UUID,
        db: AsyncSession,
        trigger_data: dict | None = None,
    ) -> dict:
        """Execute all steps in a workflow in dependency order."""
        log = logger.bind(workflow_id=str(workflow_id))

        result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
        workflow = result.scalar_one_or_none()
        if not workflow:
            log.error("workflow_not_found")
            raise ValueError("Workflow not found")

        steps_result = await db.execute(
            select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id)
        )
        steps = list(steps_result.scalars().all())
        if not steps:
            log.warning("workflow_no_steps")
            return {"status": "completed", "message": "No steps to execute"}

        # Build execution plan via topological sort
        try:
            layers = self._topological_sort(steps)
        except ValueError as exc:
            log.error("workflow_cycle_detected", error=str(exc))
            workflow.status = "failed"
            await db.flush()
            return {"status": "failed", "error": str(exc)}

        workflow.status = "running"
        await db.flush()

        await self._emit_event("workflow_started", {
            "workflow_id": str(workflow_id),
            "workflow_name": workflow.name,
            "total_steps": len(steps),
            "layers": len(layers),
        })

        context: dict = {"trigger_data": trigger_data or {}, "steps": {}}
        failed = False

        for layer_idx, layer in enumerate(layers):
            log.info("workflow_executing_layer", layer=layer_idx, steps=len(layer))

            if len(layer) == 1:
                step_result = await self.execute_step(layer[0], context, db)
                context["steps"][str(layer[0].id)] = step_result
                if step_result.get("status") == "failed":
                    # Attempt retry if configured
                    retry_result = await self._retry_if_configured(layer[0], context, db)
                    if retry_result and retry_result.get("status") != "failed":
                        context["steps"][str(layer[0].id)] = retry_result
                    else:
                        failed = True
                        break
            else:
                # Execute steps in this layer concurrently
                tasks = [self.execute_step(s, context, db) for s in layer]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for step, step_result in zip(layer, results, strict=True):
                    if isinstance(step_result, Exception):
                        context["steps"][str(step.id)] = {"status": "failed", "error": str(step_result)}
                        failed = True
                    else:
                        context["steps"][str(step.id)] = step_result
                        if step_result.get("status") == "failed":
                            failed = True
                if failed:
                    break

        # Save final state
        final_status = "failed" if failed else "completed"
        workflow.status = final_status
        await db.flush()

        await self._save_state(workflow_id, {
            "status": final_status,
            "context": context,
            "completed_at": datetime.now(UTC).isoformat(),
        })

        await self._emit_event("workflow_completed", {
            "workflow_id": str(workflow_id),
            "status": final_status,
        })

        log.info("workflow_execution_finished", status=final_status)
        return {"status": final_status, "context": context}

    async def _retry_if_configured(
        self,
        step: WorkflowStep,
        context: dict,
        db: AsyncSession,
    ) -> dict | None:
        """Retry a failed step according to its retry policy."""
        config = step.config or {}
        max_retries = config.get("max_retries", 0)
        retry_delay = config.get("retry_delay_seconds", 5)

        for attempt in range(1, max_retries + 1):
            logger.info("workflow_step_retry", step_id=str(step.id), attempt=attempt)
            await asyncio.sleep(min(retry_delay * attempt, 60))
            result = await self.execute_step(step, context, db)
            if result.get("status") != "failed":
                return result

        return None

    # ------------------------------------------------------------------
    # Status and control
    # ------------------------------------------------------------------

    async def get_workflow_status(self, workflow_id: uuid.UUID, db: AsyncSession) -> dict:
        """Get current workflow execution status."""
        result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
        workflow = result.scalar_one_or_none()
        if not workflow:
            raise ValueError("Workflow not found")

        steps_result = await db.execute(
            select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id).order_by(WorkflowStep.order)
        )
        steps = list(steps_result.scalars().all())

        # Try to load cached state from Redis
        cached = await self._load_state(workflow_id)

        return {
            "workflow_id": str(workflow_id),
            "name": workflow.name,
            "status": workflow.status,
            "steps": [
                {
                    "id": str(s.id),
                    "name": s.name,
                    "type": s.step_type,
                    "status": s.status,
                    "order": s.order,
                    "depends_on": s.depends_on,
                }
                for s in steps
            ],
            "cached_state": cached,
        }

    async def cancel_workflow(self, workflow_id: uuid.UUID, db: AsyncSession) -> bool:
        """Cancel a running workflow."""
        log = logger.bind(workflow_id=str(workflow_id))

        result = await db.execute(select(Workflow).where(Workflow.id == workflow_id))
        workflow = result.scalar_one_or_none()
        if not workflow:
            log.warning("workflow_not_found")
            return False

        if workflow.status not in ("running", "draft", "active"):
            log.warning("workflow_not_cancellable", status=workflow.status)
            return False

        workflow.status = "cancelled"

        # Cancel pending/running steps
        steps_result = await db.execute(
            select(WorkflowStep).where(
                and_(
                    WorkflowStep.workflow_id == workflow_id,
                    WorkflowStep.status.in_(["pending", "running"]),
                )
            )
        )
        for step in steps_result.scalars().all():
            step.status = "cancelled"

        await db.flush()

        await self._emit_event("workflow_cancelled", {
            "workflow_id": str(workflow_id),
        })

        log.info("workflow_cancelled")
        return True

    async def retry_step(
        self,
        workflow_id: uuid.UUID,
        step_id: uuid.UUID,
        db: AsyncSession,
    ) -> dict:
        """Retry a specific failed step in a workflow."""
        log = logger.bind(workflow_id=str(workflow_id), step_id=str(step_id))

        result = await db.execute(
            select(WorkflowStep).where(
                and_(WorkflowStep.id == step_id, WorkflowStep.workflow_id == workflow_id)
            )
        )
        step = result.scalar_one_or_none()
        if not step:
            raise ValueError("Step not found")

        if step.status != "failed":
            log.warning("step_not_failed", status=step.status)
            raise ValueError(f"Step is not in failed state (current: {step.status})")

        # Reset step and re-execute
        step.status = "pending"
        await db.flush()

        cached = await self._load_state(workflow_id)
        context = cached.get("context", {}) if cached else {"trigger_data": {}, "steps": {}}

        step_result = await self.execute_step(step, context, db)
        context["steps"][str(step.id)] = step_result
        await self._save_state(workflow_id, {"status": "running", "context": context})

        log.info("workflow_step_retried", result_status=step_result.get("status"))
        return step_result


workflow_engine = WorkflowEngine()
