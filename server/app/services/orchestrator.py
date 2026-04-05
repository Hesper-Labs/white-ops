"""Task orchestrator - distributes tasks to available agents."""

import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent import Agent
from app.models.task import Task

logger = structlog.get_logger()


class TaskOrchestrator:
    async def assign_task(self, task_id: uuid.UUID, db: AsyncSession) -> Agent | None:
        """Find the best available agent for a task and assign it."""
        result = await db.execute(select(Task).where(Task.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return None

        # Find available agents
        query = select(Agent).where(
            Agent.is_active.is_(True),
            Agent.status == "idle",
        )

        # Filter by required tools if specified
        result = await db.execute(query)
        agents = list(result.scalars().all())

        if not agents:
            logger.warning("no_available_agents", task_id=str(task_id))
            return None

        # Simple round-robin for now - pick agent with fewest active tasks
        best_agent = min(agents, key=lambda a: a.tasks_completed)

        task.agent_id = best_agent.id
        task.status = "assigned"
        await db.flush()

        logger.info(
            "task_assigned",
            task_id=str(task_id),
            agent_id=str(best_agent.id),
            agent_name=best_agent.name,
        )
        return best_agent

    async def redistribute_tasks(self, worker_id: uuid.UUID, db: AsyncSession) -> int:
        """Redistribute tasks from a failed worker's agents to other agents."""
        # Find agents on the failed worker
        agents_result = await db.execute(
            select(Agent).where(Agent.worker_id == worker_id)
        )
        failed_agents = list(agents_result.scalars().all())

        redistributed = 0
        for agent in failed_agents:
            # Find in-progress tasks
            tasks_result = await db.execute(
                select(Task).where(
                    Task.agent_id == agent.id,
                    Task.status.in_(["assigned", "in_progress"]),
                )
            )
            tasks = list(tasks_result.scalars().all())

            for task in tasks:
                task.status = "pending"
                task.agent_id = None
                redistributed += 1

            agent.status = "offline"

        if redistributed:
            logger.info(
                "tasks_redistributed",
                worker_id=str(worker_id),
                count=redistributed,
            )

        return redistributed


orchestrator = TaskOrchestrator()
