"""Task orchestrator - distributes tasks to available agents with smart assignment."""

import json
import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.agent import Agent
from app.models.task import Task
from app.models.worker import Worker

logger = structlog.get_logger()

# Priority ordering for task assignment (lower number = assign first)
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


class TaskOrchestrator:
    def __init__(self):
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        """Get or create an async Redis connection."""
        if self._redis is None or self._redis.connection is not None and self._redis.connection.is_connected is False:
            self._redis = aioredis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=0,
                decode_responses=True,
            )
        return self._redis

    async def assign_task(self, task_id: uuid.UUID, db: AsyncSession) -> Agent | None:
        """Find the best available agent for a task using smart assignment.

        Algorithm:
        1. Filter agents that are active and have capacity (active tasks < max_concurrent)
        2. Filter agents whose enabled_tools cover the task's required_tools
        3. Score remaining agents by worker load (prefer lowest resource usage)
        4. Assign to the best-scoring agent
        """
        log = logger.bind(task_id=str(task_id))

        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            log.error("task_not_found")
            return None

        if task.status not in ("pending", "failed"):
            log.warning("task_not_assignable", current_status=task.status)
            return None

        required_tools = task.required_tools or []

        # Find active agents with their workers, excluding offline/error agents
        agent_query = (
            select(Agent, Worker)
            .outerjoin(Worker, Agent.worker_id == Worker.id)
            .where(
                and_(
                    Agent.is_active.is_(True),
                    Agent.status.in_(["idle", "busy"]),
                )
            )
        )
        result = await db.execute(agent_query)
        agent_worker_pairs = result.all()

        if not agent_worker_pairs:
            log.warning("no_active_agents")
            return None

        # Count active tasks per agent (assigned + in_progress)
        active_task_counts_result = await db.execute(
            select(Task.agent_id, func.count(Task.id))
            .where(Task.status.in_(["assigned", "in_progress"]))
            .group_by(Task.agent_id)
        )
        active_task_counts = dict(active_task_counts_result.all())

        candidates = []
        for agent, worker in agent_worker_pairs:
            active_count = active_task_counts.get(agent.id, 0)

            # Skip agents at capacity
            if active_count >= agent.max_concurrent_tasks:
                log.debug("agent_at_capacity", agent_id=str(agent.id),
                          agent_name=agent.name, active=active_count,
                          max=agent.max_concurrent_tasks)
                continue

            # Check tool requirements
            if required_tools:
                agent_tools = set()
                if isinstance(agent.enabled_tools, dict):
                    agent_tools = {k for k, v in agent.enabled_tools.items() if v}
                elif isinstance(agent.enabled_tools, list):
                    agent_tools = set(agent.enabled_tools)

                missing_tools = set(required_tools) - agent_tools
                if missing_tools:
                    log.debug("agent_missing_tools", agent_id=str(agent.id),
                              agent_name=agent.name, missing=list(missing_tools))
                    continue

            # Skip agents on offline/error workers
            if worker and worker.status not in ("online",):
                log.debug("agent_worker_not_online", agent_id=str(agent.id),
                          worker_status=worker.status if worker else "no_worker")
                continue

            # Compute a score (lower is better)
            # Components:
            #   - Capacity utilization: active_count / max_concurrent (0-1)
            #   - Worker CPU load: cpu_usage / 100 (0-1)
            #   - Worker memory load: memory_usage / 100 (0-1)
            capacity_ratio = active_count / max(agent.max_concurrent_tasks, 1)
            cpu_load = (worker.cpu_usage_percent / 100.0) if worker else 0.5
            mem_load = (worker.memory_usage_percent / 100.0) if worker else 0.5

            # Weighted score: capacity matters most, then CPU, then memory
            score = (capacity_ratio * 0.5) + (cpu_load * 0.3) + (mem_load * 0.2)

            candidates.append({
                "agent": agent,
                "worker": worker,
                "score": score,
                "active_tasks": active_count,
            })

        if not candidates:
            log.warning("no_eligible_agents",
                        required_tools=required_tools,
                        total_agents=len(agent_worker_pairs))
            return None

        # Sort by score ascending (best candidate first)
        candidates.sort(key=lambda c: c["score"])
        best = candidates[0]
        best_agent = best["agent"]

        # Assign the task
        task.agent_id = best_agent.id
        task.status = "assigned"
        await db.flush()

        # Update agent status if it was idle
        if best_agent.status == "idle":
            best_agent.status = "busy"
            await db.flush()

        log.info("task_assigned",
                 agent_id=str(best_agent.id),
                 agent_name=best_agent.name,
                 score=round(best["score"], 3),
                 active_tasks=best["active_tasks"],
                 worker_id=str(best["worker"].id) if best["worker"] else None,
                 candidates_evaluated=len(candidates))

        return best_agent

    async def queue_task(self, task_id: uuid.UUID, db: AsyncSession) -> bool:
        """Add a task to the Redis queue for async processing by the Celery worker.

        Tries to assign immediately; if no agent is available, queues for later.
        Tasks are ordered by priority.
        """
        log = logger.bind(task_id=str(task_id))

        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            log.error("task_not_found")
            return False

        # Try immediate assignment
        agent = await self.assign_task(task_id, db)
        if agent:
            # Dispatch to Celery for execution
            from app.services.task_queue import execute_task
            execute_task.delay(str(task_id), str(agent.id))
            log.info("task_queued_and_assigned", agent_id=str(agent.id))
            return True

        # No agent available -- push to priority-sorted Redis queue
        r = await self._get_redis()
        priority_score = PRIORITY_ORDER.get(task.priority, 2)
        await r.zadd("whiteops:tasks:waiting", {str(task_id): priority_score})

        log.info("task_queued_for_later", priority=task.priority)
        return True

    async def cancel_task(self, task_id: uuid.UUID, db: AsyncSession, reason: str = "cancelled by user") -> bool:
        """Cancel a running or pending task and notify the worker."""
        log = logger.bind(task_id=str(task_id))

        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            log.error("task_not_found")
            return False

        if task.status in ("completed", "cancelled"):
            log.warning("task_already_terminal", status=task.status)
            return False

        previous_status = task.status
        agent_id = task.agent_id
        task.status = "cancelled"
        task.error = reason
        task.agent_id = None
        await db.flush()

        # If the task was assigned to an agent, notify the worker to stop
        if agent_id and previous_status in ("assigned", "in_progress"):
            agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = agent_result.scalar_one_or_none()

            if agent and agent.worker_id:
                r = await self._get_redis()
                channel = f"whiteops:tasks:{agent.worker_id}"
                await r.publish(channel, json.dumps({
                    "action": "cancel",
                    "task_id": str(task_id),
                    "agent_id": str(agent_id),
                    "reason": reason,
                }))
                log.info("cancel_notification_sent", worker_id=str(agent.worker_id))

            # Check if agent has other active tasks; if not, set to idle
            remaining = await db.execute(
                select(func.count(Task.id)).where(
                    and_(
                        Task.agent_id == agent_id,
                        Task.status.in_(["assigned", "in_progress"]),
                    )
                )
            )
            if remaining.scalar() == 0 and agent:
                agent.status = "idle"
                await db.flush()

        log.info("task_cancelled", previous_status=previous_status)
        return True

    async def retry_task(self, task_id: uuid.UUID, db: AsyncSession) -> bool:
        """Retry a failed task with incremented retry count and exponential backoff."""
        log = logger.bind(task_id=str(task_id))

        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            log.error("task_not_found")
            return False

        if task.status != "failed":
            log.warning("task_not_failed", status=task.status)
            return False

        if task.retry_count >= task.max_retries:
            log.warning("task_max_retries_reached",
                        retry_count=task.retry_count, max_retries=task.max_retries)
            return False

        task.retry_count += 1
        task.status = "pending"
        task.agent_id = None
        task.error = None
        task.started_at = None
        await db.flush()

        log.info("task_retry_scheduled", retry_count=task.retry_count)

        # Queue for reassignment
        await self.queue_task(task_id, db)
        return True

    async def redistribute_tasks(self, worker_id: uuid.UUID, db: AsyncSession) -> int:
        """Redistribute tasks from a failed worker's agents to other agents.

        Marks the worker's agents as offline, resets their active tasks to pending,
        and attempts to reassign critical/high priority tasks immediately.
        """
        log = logger.bind(worker_id=str(worker_id))

        # Find agents on the failed worker
        agents_result = await db.execute(
            select(Agent).where(Agent.worker_id == worker_id)
        )
        failed_agents = list(agents_result.scalars().all())

        if not failed_agents:
            log.info("no_agents_on_worker")
            return 0

        redistributed = 0
        critical_task_ids = []

        for agent in failed_agents:
            # Find active tasks
            tasks_result = await db.execute(
                select(Task).where(
                    and_(
                        Task.agent_id == agent.id,
                        Task.status.in_(["assigned", "in_progress"]),
                    )
                )
            )
            tasks = list(tasks_result.scalars().all())

            for task in tasks:
                task.status = "pending"
                task.agent_id = None
                task.error = f"Worker {worker_id} failed, task redistributed"
                redistributed += 1

                if task.priority in ("critical", "high"):
                    critical_task_ids.append(task.id)

            agent.status = "offline"

        await db.flush()

        # Notify via Redis about the worker failure
        r = await self._get_redis()
        await r.publish("whiteops:events:worker_failure", json.dumps({
            "worker_id": str(worker_id),
            "agents_affected": len(failed_agents),
            "tasks_redistributed": redistributed,
            "timestamp": datetime.now(UTC).isoformat(),
        }))

        # Attempt immediate reassignment of critical/high priority tasks
        reassigned = 0
        for tid in critical_task_ids:
            agent = await self.assign_task(tid, db)
            if agent:
                from app.services.task_queue import execute_task
                execute_task.delay(str(tid), str(agent.id))
                reassigned += 1

        log.info("tasks_redistributed",
                 count=redistributed,
                 critical_reassigned=reassigned,
                 agents_marked_offline=len(failed_agents))

        return redistributed

    async def get_task_metrics(self, db: AsyncSession) -> dict:
        """Return current task assignment and orchestrator metrics."""
        # Tasks by status
        status_counts_result = await db.execute(
            select(Task.status, func.count(Task.id)).group_by(Task.status)
        )
        status_counts = dict(status_counts_result.all())

        # Tasks by priority (active only)
        priority_counts_result = await db.execute(
            select(Task.priority, func.count(Task.id))
            .where(Task.status.in_(["pending", "assigned", "in_progress"]))
            .group_by(Task.priority)
        )
        priority_counts = dict(priority_counts_result.all())

        # Agent utilization
        total_agents = await db.execute(
            select(func.count(Agent.id)).where(Agent.is_active.is_(True))
        )
        total_agents_count = total_agents.scalar() or 0

        idle_agents = await db.execute(
            select(func.count(Agent.id)).where(
                and_(Agent.is_active.is_(True), Agent.status == "idle")
            )
        )
        idle_count = idle_agents.scalar() or 0

        busy_agents = await db.execute(
            select(func.count(Agent.id)).where(
                and_(Agent.is_active.is_(True), Agent.status == "busy")
            )
        )
        busy_count = busy_agents.scalar() or 0

        # Average tasks per busy agent
        await db.execute(  # result unused; query warms the planner cache
            select(func.avg(func.count(Task.id)))
            .select_from(Task)
            .where(Task.status.in_(["assigned", "in_progress"]))
            .group_by(Task.agent_id)
        )
        # This subquery approach is simpler
        active_tasks_per_agent = await db.execute(
            select(Task.agent_id, func.count(Task.id).label("cnt"))
            .where(
                and_(
                    Task.status.in_(["assigned", "in_progress"]),
                    Task.agent_id.isnot(None),
                )
            )
            .group_by(Task.agent_id)
        )
        per_agent = active_tasks_per_agent.all()
        avg_active = sum(r[1] for r in per_agent) / len(per_agent) if per_agent else 0.0

        # Waiting queue size from Redis
        r = await self._get_redis()
        waiting_count = await r.zcard("whiteops:tasks:waiting")

        return {
            "tasks_by_status": status_counts,
            "active_tasks_by_priority": priority_counts,
            "agents": {
                "total_active": total_agents_count,
                "idle": idle_count,
                "busy": busy_count,
                "avg_active_tasks_per_agent": round(avg_active, 2),
            },
            "waiting_queue_size": waiting_count,
            "timestamp": datetime.now(UTC).isoformat(),
        }


orchestrator = TaskOrchestrator()
