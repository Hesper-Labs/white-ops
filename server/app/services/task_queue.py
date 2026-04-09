"""Celery task queue for distributed task execution."""

import json
import uuid
from datetime import datetime, timedelta, timezone

import redis
import structlog
from celery import Celery
from celery.schedules import crontab
from minio import Minio
from sqlalchemy import select, func, and_

from app.config import settings

logger = structlog.get_logger()

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
        "app.services.task_queue.cleanup_old_files": {"queue": "maintenance"},
        "app.services.task_queue.generate_analytics_snapshot": {"queue": "analytics"},
        "app.services.task_queue.check_worker_health": {"queue": "maintenance"},
        "app.services.task_queue.process_dead_letter": {"queue": "maintenance"},
    },
    beat_schedule={
        "cleanup-old-files-daily": {
            "task": "app.services.task_queue.cleanup_old_files",
            "schedule": crontab(hour=3, minute=0),
            "args": (30,),
        },
        "analytics-snapshot-hourly": {
            "task": "app.services.task_queue.generate_analytics_snapshot",
            "schedule": crontab(minute=0),
        },
        "check-worker-health": {
            "task": "app.services.task_queue.check_worker_health",
            "schedule": 60.0,  # every 60 seconds
        },
        "process-dead-letter-queue": {
            "task": "app.services.task_queue.process_dead_letter",
            "schedule": crontab(minute="*/5"),
        },
    },
)


def _get_sync_redis() -> redis.Redis:
    """Get a synchronous Redis client for use inside Celery tasks."""
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password,
        db=0,
        decode_responses=True,
    )


def _get_sync_db_session():
    """Get a synchronous DB session for use inside Celery tasks.

    Celery tasks run in sync context, so we use a synchronous engine.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    sync_url = settings.database_url.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True, pool_size=5)
    Session = sessionmaker(bind=engine)
    return Session()


def _get_minio_client() -> Minio:
    """Get a MinIO client instance."""
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=False,
    )


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def execute_task(self, task_id: str, agent_id: str) -> dict:
    """Execute a task by dispatching it to the assigned worker via Redis pub/sub."""
    log = logger.bind(task_id=task_id, agent_id=agent_id, celery_task_id=self.request.id)
    log.info("execute_task_started")

    db = _get_sync_db_session()
    try:
        from app.models.task import Task
        from app.models.agent import Agent

        task = db.execute(
            select(Task).where(Task.id == uuid.UUID(task_id))
        ).scalar_one_or_none()
        if not task:
            log.error("task_not_found")
            return {"task_id": task_id, "status": "error", "error": "Task not found"}

        agent = db.execute(
            select(Agent).where(Agent.id == uuid.UUID(agent_id))
        ).scalar_one_or_none()
        if not agent:
            log.error("agent_not_found")
            return {"task_id": task_id, "status": "error", "error": "Agent not found"}

        if not agent.worker_id:
            log.error("agent_has_no_worker")
            return {"task_id": task_id, "status": "error", "error": "Agent has no worker assigned"}

        worker_id = str(agent.worker_id)

        # Update task status to in_progress
        task.status = "in_progress"
        task.started_at = datetime.now(timezone.utc)
        db.commit()

        # Publish task assignment to the worker's Redis channel
        r = _get_sync_redis()
        channel = f"whiteops:tasks:{worker_id}"
        payload = json.dumps({
            "action": "execute",
            "task_id": task_id,
            "agent_id": agent_id,
            "task": {
                "title": task.title,
                "description": task.description,
                "instructions": task.instructions,
                "required_tools": task.required_tools,
                "priority": task.priority,
                "max_retries": task.max_retries,
                "retry_count": task.retry_count,
            },
            "agent": {
                "name": agent.name,
                "role": agent.role,
                "llm_provider": agent.llm_provider,
                "llm_model": agent.llm_model,
                "system_prompt": agent.system_prompt,
                "temperature": agent.temperature,
                "max_tokens": agent.max_tokens,
                "enabled_tools": agent.enabled_tools,
            },
        })

        subscribers = r.publish(channel, payload)
        log.info("task_dispatched_to_worker", worker_id=worker_id, subscribers=subscribers)

        if subscribers == 0:
            log.warning("no_subscribers_on_channel", channel=channel)
            # Push to a fallback list so the worker can pick it up when it reconnects
            r.rpush(f"whiteops:pending:{worker_id}", payload)

        return {
            "task_id": task_id,
            "agent_id": agent_id,
            "worker_id": worker_id,
            "status": "dispatched",
            "subscribers": subscribers,
        }

    except Exception as exc:
        log.error("execute_task_failed", error=str(exc))
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            log.error("execute_task_max_retries_exceeded")
            # Mark task as failed in DB
            try:
                task = db.execute(
                    select(Task).where(Task.id == uuid.UUID(task_id))
                ).scalar_one_or_none()
                if task:
                    task.status = "failed"
                    task.error = f"Max retries exceeded: {exc}"
                    db.commit()
            except Exception:
                db.rollback()
            # Push to dead letter queue
            try:
                r = _get_sync_redis()
                r.rpush("whiteops:dlq", json.dumps({
                    "task_id": task_id,
                    "agent_id": agent_id,
                    "error": str(exc),
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                }))
            except Exception:
                pass
            return {"task_id": task_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=30)
def scheduled_task(self, schedule_id: str) -> dict:
    """Execute a scheduled/recurring task by looking up the schedule and creating a new task."""
    log = logger.bind(schedule_id=schedule_id)
    log.info("scheduled_task_triggered")

    db = _get_sync_db_session()
    try:
        from app.models.task import Task

        # Look up the schedule template -- stored as a task with metadata
        template = db.execute(
            select(Task).where(Task.id == uuid.UUID(schedule_id))
        ).scalar_one_or_none()

        if not template:
            log.error("schedule_template_not_found")
            return {"schedule_id": schedule_id, "status": "error", "error": "Schedule not found"}

        # Create a new task instance from the template
        new_task = Task(
            title=f"{template.title} (scheduled {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')})",
            description=template.description,
            instructions=template.instructions,
            status="pending",
            priority=template.priority,
            required_tools=template.required_tools,
            max_retries=template.max_retries,
            workflow_id=template.workflow_id,
            parent_task_id=template.id,
            metadata_={"scheduled_from": schedule_id, "scheduled_at": datetime.now(timezone.utc).isoformat()},
        )
        db.add(new_task)
        db.flush()

        new_task_id = str(new_task.id)
        db.commit()

        log.info("scheduled_task_created", new_task_id=new_task_id)

        # Dispatch the new task for assignment via the orchestrator queue
        r = _get_sync_redis()
        r.rpush("whiteops:tasks:pending", json.dumps({
            "task_id": new_task_id,
            "source": "scheduler",
            "schedule_id": schedule_id,
        }))

        return {
            "schedule_id": schedule_id,
            "new_task_id": new_task_id,
            "status": "created",
        }

    except Exception as exc:
        db.rollback()
        log.error("scheduled_task_failed", error=str(exc))
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            log.error("scheduled_task_max_retries_exceeded")
            return {"schedule_id": schedule_id, "status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1)
def cleanup_old_files(self, days: int = 30) -> dict:
    """Clean up files older than N days from MinIO storage."""
    log = logger.bind(days=days)
    log.info("cleanup_old_files_started")

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    deleted_count = 0
    errors = []

    try:
        minio_client = _get_minio_client()
        bucket = settings.minio_bucket

        if not minio_client.bucket_exists(bucket):
            log.warning("bucket_not_found", bucket=bucket)
            return {"days": days, "deleted": 0, "status": "bucket_not_found"}

        # List and delete old objects
        objects = minio_client.list_objects(bucket, recursive=True)
        objects_to_delete = []

        for obj in objects:
            if obj.last_modified and obj.last_modified < cutoff:
                objects_to_delete.append(obj.object_name)

        for obj_name in objects_to_delete:
            try:
                minio_client.remove_object(bucket, obj_name)
                deleted_count += 1
                log.debug("file_deleted", object_name=obj_name)
            except Exception as e:
                errors.append({"object": obj_name, "error": str(e)})
                log.warning("file_delete_failed", object_name=obj_name, error=str(e))

        # Also clean up output_files references in completed tasks
        db = _get_sync_db_session()
        try:
            from app.models.task import Task
            old_tasks = db.execute(
                select(Task).where(
                    and_(
                        Task.status.in_(["completed", "failed", "cancelled"]),
                        Task.completed_at < cutoff,
                        Task.output_files != [],
                    )
                )
            ).scalars().all()

            for task in old_tasks:
                task.output_files = []

            db.commit()
        except Exception as e:
            db.rollback()
            log.warning("db_cleanup_failed", error=str(e))
        finally:
            db.close()

        log.info("cleanup_old_files_completed", deleted=deleted_count, errors=len(errors))
        return {
            "days": days,
            "deleted": deleted_count,
            "errors": len(errors),
            "status": "completed",
        }

    except Exception as exc:
        log.error("cleanup_old_files_failed", error=str(exc))
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"days": days, "status": "failed", "error": str(exc)}


@celery_app.task(bind=True, max_retries=1)
def generate_analytics_snapshot(self) -> dict:
    """Generate periodic analytics snapshot aggregating task and agent metrics."""
    log = logger.bind()
    log.info("generate_analytics_snapshot_started")

    db = _get_sync_db_session()
    try:
        from app.models.task import Task
        from app.models.agent import Agent
        from app.models.worker import Worker

        now = datetime.now(timezone.utc)
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        # Task metrics
        total_tasks = db.execute(select(func.count(Task.id))).scalar() or 0
        pending_tasks = db.execute(
            select(func.count(Task.id)).where(Task.status == "pending")
        ).scalar() or 0
        in_progress_tasks = db.execute(
            select(func.count(Task.id)).where(Task.status == "in_progress")
        ).scalar() or 0
        completed_last_hour = db.execute(
            select(func.count(Task.id)).where(
                and_(Task.status == "completed", Task.completed_at >= hour_ago)
            )
        ).scalar() or 0
        completed_last_day = db.execute(
            select(func.count(Task.id)).where(
                and_(Task.status == "completed", Task.completed_at >= day_ago)
            )
        ).scalar() or 0
        failed_last_day = db.execute(
            select(func.count(Task.id)).where(
                and_(Task.status == "failed", Task.updated_at >= day_ago)
            )
        ).scalar() or 0

        # Task priority breakdown
        priority_counts = {}
        for priority in ("critical", "high", "medium", "low"):
            count = db.execute(
                select(func.count(Task.id)).where(
                    and_(Task.status.in_(["pending", "assigned", "in_progress"]), Task.priority == priority)
                )
            ).scalar() or 0
            priority_counts[priority] = count

        # Agent metrics
        total_agents = db.execute(
            select(func.count(Agent.id)).where(Agent.is_active.is_(True))
        ).scalar() or 0
        idle_agents = db.execute(
            select(func.count(Agent.id)).where(
                and_(Agent.is_active.is_(True), Agent.status == "idle")
            )
        ).scalar() or 0
        busy_agents = db.execute(
            select(func.count(Agent.id)).where(
                and_(Agent.is_active.is_(True), Agent.status == "busy")
            )
        ).scalar() or 0
        error_agents = db.execute(
            select(func.count(Agent.id)).where(
                and_(Agent.is_active.is_(True), Agent.status == "error")
            )
        ).scalar() or 0
        total_completed = db.execute(
            select(func.sum(Agent.tasks_completed)).where(Agent.is_active.is_(True))
        ).scalar() or 0
        total_failed = db.execute(
            select(func.sum(Agent.tasks_failed)).where(Agent.is_active.is_(True))
        ).scalar() or 0

        # Worker metrics
        online_workers = db.execute(
            select(func.count(Worker.id)).where(Worker.status == "online")
        ).scalar() or 0
        avg_cpu = db.execute(
            select(func.avg(Worker.cpu_usage_percent)).where(Worker.status == "online")
        ).scalar() or 0.0
        avg_memory = db.execute(
            select(func.avg(Worker.memory_usage_percent)).where(Worker.status == "online")
        ).scalar() or 0.0

        snapshot = {
            "timestamp": now.isoformat(),
            "tasks": {
                "total": total_tasks,
                "pending": pending_tasks,
                "in_progress": in_progress_tasks,
                "completed_last_hour": completed_last_hour,
                "completed_last_day": completed_last_day,
                "failed_last_day": failed_last_day,
                "priority_breakdown": priority_counts,
            },
            "agents": {
                "total_active": total_agents,
                "idle": idle_agents,
                "busy": busy_agents,
                "error": error_agents,
                "total_completed": total_completed,
                "total_failed": total_failed,
            },
            "workers": {
                "online": online_workers,
                "avg_cpu_percent": round(float(avg_cpu), 2),
                "avg_memory_percent": round(float(avg_memory), 2),
            },
        }

        # Store snapshot in Redis with TTL of 7 days
        r = _get_sync_redis()
        snapshot_key = f"whiteops:analytics:{now.strftime('%Y%m%d%H%M')}"
        r.setex(snapshot_key, timedelta(days=7), json.dumps(snapshot))
        r.set("whiteops:analytics:latest", json.dumps(snapshot))

        log.info("analytics_snapshot_generated", snapshot_key=snapshot_key)
        return {"status": "generated", "snapshot_key": snapshot_key, "snapshot": snapshot}

    except Exception as exc:
        log.error("generate_analytics_snapshot_failed", error=str(exc))
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1)
def check_worker_health(self) -> dict:
    """Check worker heartbeats and mark stale workers as offline."""
    log = logger.bind()
    log.info("check_worker_health_started")

    db = _get_sync_db_session()
    try:
        from app.models.worker import Worker
        from app.models.agent import Agent
        from app.models.task import Task

        stale_threshold = datetime.now(timezone.utc) - timedelta(seconds=90)

        # Find workers that are online but have stale heartbeats
        stale_workers = db.execute(
            select(Worker).where(
                and_(
                    Worker.status == "online",
                    Worker.last_heartbeat < stale_threshold,
                )
            )
        ).scalars().all()

        marked_offline = 0
        tasks_requeued = 0

        for worker in stale_workers:
            log.warning("worker_stale_heartbeat", worker_id=str(worker.id), worker_name=worker.name,
                        last_heartbeat=worker.last_heartbeat.isoformat() if worker.last_heartbeat else None)

            worker.status = "offline"
            marked_offline += 1

            # Mark all agents on this worker as offline
            agents = db.execute(
                select(Agent).where(Agent.worker_id == worker.id)
            ).scalars().all()

            for agent in agents:
                agent.status = "offline"

                # Requeue any active tasks from this agent
                active_tasks = db.execute(
                    select(Task).where(
                        and_(
                            Task.agent_id == agent.id,
                            Task.status.in_(["assigned", "in_progress"]),
                        )
                    )
                ).scalars().all()

                for task in active_tasks:
                    task.status = "pending"
                    task.agent_id = None
                    task.error = f"Worker {worker.name} went offline"
                    tasks_requeued += 1

        db.commit()

        # Publish worker status changes
        if marked_offline > 0:
            r = _get_sync_redis()
            r.publish("whiteops:events:worker_health", json.dumps({
                "workers_marked_offline": marked_offline,
                "tasks_requeued": tasks_requeued,
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }))

        log.info("check_worker_health_completed",
                 marked_offline=marked_offline, tasks_requeued=tasks_requeued)
        return {
            "status": "completed",
            "marked_offline": marked_offline,
            "tasks_requeued": tasks_requeued,
        }

    except Exception as exc:
        db.rollback()
        log.error("check_worker_health_failed", error=str(exc))
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}
    finally:
        db.close()


@celery_app.task(bind=True, max_retries=1)
def process_dead_letter(self) -> dict:
    """Process failed tasks from the dead letter queue and retry eligible ones."""
    log = logger.bind()
    log.info("process_dead_letter_started")

    r = _get_sync_redis()
    db = _get_sync_db_session()
    processed = 0
    retried = 0
    discarded = 0

    try:
        from app.models.task import Task

        # Process up to 50 items from DLQ per run
        batch_size = 50
        for _ in range(batch_size):
            raw = r.lpop("whiteops:dlq")
            if not raw:
                break

            processed += 1
            try:
                item = json.loads(raw)
            except json.JSONDecodeError:
                log.warning("dlq_invalid_json", raw=raw[:200])
                discarded += 1
                continue

            task_id = item.get("task_id")
            if not task_id:
                discarded += 1
                continue

            task = db.execute(
                select(Task).where(Task.id == uuid.UUID(task_id))
            ).scalar_one_or_none()

            if not task:
                log.warning("dlq_task_not_found", task_id=task_id)
                discarded += 1
                continue

            # Check if task is eligible for retry
            if task.retry_count >= task.max_retries:
                log.info("dlq_task_max_retries", task_id=task_id,
                         retry_count=task.retry_count, max_retries=task.max_retries)
                discarded += 1
                continue

            if task.status == "cancelled":
                log.info("dlq_task_cancelled", task_id=task_id)
                discarded += 1
                continue

            # Reset task for retry
            task.status = "pending"
            task.agent_id = None
            task.retry_count += 1
            task.error = None
            retried += 1

            log.info("dlq_task_retried", task_id=task_id, retry_count=task.retry_count)

        db.commit()

        log.info("process_dead_letter_completed",
                 processed=processed, retried=retried, discarded=discarded)
        return {
            "status": "completed",
            "processed": processed,
            "retried": retried,
            "discarded": discarded,
        }

    except Exception as exc:
        db.rollback()
        log.error("process_dead_letter_failed", error=str(exc))
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return {"status": "failed", "error": str(exc)}
    finally:
        db.close()
