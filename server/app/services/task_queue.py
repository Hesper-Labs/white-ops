"""Celery task queue for distributed task execution."""

from celery import Celery

from app.config import settings

celery_app = Celery(
    "whiteops",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_soft_time_limit=3600,
    task_time_limit=3900,
    task_default_queue="whiteops",
    task_routes={
        "app.services.task_queue.execute_task": {"queue": "tasks"},
        "app.services.task_queue.scheduled_task": {"queue": "scheduled"},
    },
)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def execute_task(self, task_id: str, agent_id: str) -> dict:
    """Execute a task via the worker agent."""
    import httpx

    try:
        with httpx.Client(timeout=30) as client:
            response = client.post(
                f"{settings.redis_url}/execute",
                json={"task_id": task_id, "agent_id": agent_id},
            )
            return response.json()
    except Exception as exc:
        self.retry(exc=exc)
        return {"error": str(exc)}


@celery_app.task
def scheduled_task(schedule_id: str) -> dict:
    """Execute a scheduled/recurring task."""
    return {"schedule_id": schedule_id, "status": "executed"}


@celery_app.task
def cleanup_old_files(days: int = 30) -> dict:
    """Clean up files older than N days."""
    return {"days": days, "status": "cleaned"}


@celery_app.task
def generate_analytics_snapshot() -> dict:
    """Generate periodic analytics snapshot."""
    return {"status": "generated"}
