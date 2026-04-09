"""Project tracker tool - manage projects, milestones, and tasks."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

STORAGE_PATH = "/tmp/whiteops_projects.json"
MAX_OUTPUT_BYTES = 50 * 1024

TASK_STATUSES = ["todo", "in_progress", "review", "done"]
PRIORITIES = ["low", "medium", "high", "critical"]


def _truncate(result: str) -> str:
    if len(result) > MAX_OUTPUT_BYTES:
        return result[:MAX_OUTPUT_BYTES] + "\n... [output truncated at 50KB]"
    return result


class ProjectTrackerTool(BaseTool):
    name = "project_tracker"
    description = (
        "Track projects with milestones and tasks. Create projects, add milestones "
        "and tasks, update task status, generate reports, and list all projects. "
        "Task statuses: todo, in_progress, review, done. "
        "Data stored in /tmp/whiteops_projects.json."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "create_project",
                    "add_milestone",
                    "add_task",
                    "update_status",
                    "get_report",
                    "list_projects",
                ],
                "description": "Project tracker action.",
            },
            "project_id": {
                "type": "string",
                "description": "Project ID.",
            },
            "name": {
                "type": "string",
                "description": "Project or milestone name.",
            },
            "description": {
                "type": "string",
                "description": "Project description.",
            },
            "deadline": {
                "type": "string",
                "description": "Project deadline (YYYY-MM-DD).",
            },
            "date": {
                "type": "string",
                "description": "Milestone date (YYYY-MM-DD).",
            },
            "title": {
                "type": "string",
                "description": "Task title.",
            },
            "assignee": {
                "type": "string",
                "description": "Task assignee.",
            },
            "priority": {
                "type": "string",
                "enum": PRIORITIES,
                "description": "Task priority.",
            },
            "task_id": {
                "type": "string",
                "description": "Task ID (for update_status).",
            },
            "status": {
                "type": "string",
                "enum": TASK_STATUSES,
                "description": "Task status.",
            },
        },
        "required": ["action"],
    }

    def _load(self) -> dict:
        path = Path(STORAGE_PATH)
        if path.exists():
            return json.loads(path.read_text())
        return {"projects": {}, "next_id": 1}

    def _save(self, data: dict) -> None:
        Path(STORAGE_PATH).write_text(json.dumps(data, indent=2, ensure_ascii=False))

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "")
        logger.info("project_tracker_execute", action=action)

        try:
            db = self._load()

            if action == "create_project":
                return self._create_project(db, kwargs)
            elif action == "add_milestone":
                return self._add_milestone(db, kwargs)
            elif action == "add_task":
                return self._add_task(db, kwargs)
            elif action == "update_status":
                return self._update_status(db, kwargs)
            elif action == "get_report":
                return self._get_report(db, kwargs)
            elif action == "list_projects":
                return self._list_projects(db)
            else:
                return _truncate(json.dumps({"error": f"Unknown action: {action}"}))
        except Exception as e:
            logger.error("project_tracker_failed", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"Project tracker failed: {e}"}))

    def _create_project(self, db: dict, kwargs: dict) -> str:
        name = kwargs.get("name", "")
        if not name:
            return _truncate(json.dumps({"error": "'name' is required"}))

        pid = uuid4().hex[:8]
        project = {
            "id": pid,
            "name": name,
            "description": kwargs.get("description", ""),
            "deadline": kwargs.get("deadline", ""),
            "milestones": [],
            "tasks": [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        db["projects"][pid] = project
        self._save(db)

        logger.info("project_created", id=pid, name=name)
        return _truncate(json.dumps({"success": True, "project": project}))

    def _add_milestone(self, db: dict, kwargs: dict) -> str:
        project_id = kwargs.get("project_id", "")
        name = kwargs.get("name", "")

        if not project_id:
            return _truncate(json.dumps({"error": "'project_id' is required"}))
        if not name:
            return _truncate(json.dumps({"error": "'name' is required"}))
        if project_id not in db["projects"]:
            return _truncate(json.dumps({"error": f"Project {project_id} not found"}))

        milestone = {
            "id": uuid4().hex[:8],
            "name": name,
            "date": kwargs.get("date", ""),
            "completed": False,
            "created_at": datetime.now().isoformat(),
        }

        db["projects"][project_id]["milestones"].append(milestone)
        db["projects"][project_id]["updated_at"] = datetime.now().isoformat()
        self._save(db)

        logger.info("milestone_added", project=project_id, milestone=milestone["id"])
        return _truncate(json.dumps({"success": True, "milestone": milestone}))

    def _add_task(self, db: dict, kwargs: dict) -> str:
        project_id = kwargs.get("project_id", "")
        title = kwargs.get("title", "")

        if not project_id:
            return _truncate(json.dumps({"error": "'project_id' is required"}))
        if not title:
            return _truncate(json.dumps({"error": "'title' is required"}))
        if project_id not in db["projects"]:
            return _truncate(json.dumps({"error": f"Project {project_id} not found"}))

        priority = kwargs.get("priority", "medium")
        if priority not in PRIORITIES:
            return _truncate(json.dumps({"error": f"Invalid priority. Must be one of: {PRIORITIES}"}))

        task = {
            "id": uuid4().hex[:8],
            "title": title,
            "assignee": kwargs.get("assignee", ""),
            "priority": priority,
            "status": "todo",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        db["projects"][project_id]["tasks"].append(task)
        db["projects"][project_id]["updated_at"] = datetime.now().isoformat()
        self._save(db)

        logger.info("task_added", project=project_id, task=task["id"], priority=priority)
        return _truncate(json.dumps({"success": True, "task": task}))

    def _update_status(self, db: dict, kwargs: dict) -> str:
        project_id = kwargs.get("project_id", "")
        task_id = kwargs.get("task_id", "")
        status = kwargs.get("status", "")

        if not project_id:
            return _truncate(json.dumps({"error": "'project_id' is required"}))
        if not task_id:
            return _truncate(json.dumps({"error": "'task_id' is required"}))
        if not status:
            return _truncate(json.dumps({"error": "'status' is required"}))
        if status not in TASK_STATUSES:
            return _truncate(json.dumps({"error": f"Invalid status. Must be one of: {TASK_STATUSES}"}))

        if project_id not in db["projects"]:
            return _truncate(json.dumps({"error": f"Project {project_id} not found"}))

        for task in db["projects"][project_id]["tasks"]:
            if task["id"] == task_id:
                old_status = task["status"]
                task["status"] = status
                task["updated_at"] = datetime.now().isoformat()
                db["projects"][project_id]["updated_at"] = datetime.now().isoformat()
                self._save(db)

                logger.info("task_status_updated", task=task_id, old=old_status, new=status)
                return _truncate(json.dumps({
                    "success": True,
                    "task": task,
                    "previous_status": old_status,
                }))

        return _truncate(json.dumps({"error": f"Task {task_id} not found in project {project_id}"}))

    def _get_report(self, db: dict, kwargs: dict) -> str:
        project_id = kwargs.get("project_id", "")
        if not project_id:
            return _truncate(json.dumps({"error": "'project_id' is required"}))
        if project_id not in db["projects"]:
            return _truncate(json.dumps({"error": f"Project {project_id} not found"}))

        project = db["projects"][project_id]
        tasks = project.get("tasks", [])
        milestones = project.get("milestones", [])

        # Task stats
        status_counts = {}
        priority_counts = {}
        for task in tasks:
            s = task.get("status", "todo")
            status_counts[s] = status_counts.get(s, 0) + 1
            p = task.get("priority", "medium")
            priority_counts[p] = priority_counts.get(p, 0) + 1

        total_tasks = len(tasks)
        done_tasks = status_counts.get("done", 0)
        progress = round(done_tasks / total_tasks * 100, 1) if total_tasks > 0 else 0

        # Overdue milestones
        today = datetime.now().strftime("%Y-%m-%d")
        overdue_milestones = [
            m for m in milestones
            if m.get("date") and m["date"] < today and not m.get("completed", False)
        ]

        report = {
            "project": {
                "id": project["id"],
                "name": project["name"],
                "deadline": project.get("deadline", ""),
                "created_at": project.get("created_at", ""),
            },
            "progress_percent": progress,
            "tasks": {
                "total": total_tasks,
                "by_status": status_counts,
                "by_priority": priority_counts,
            },
            "milestones": {
                "total": len(milestones),
                "completed": sum(1 for m in milestones if m.get("completed")),
                "overdue": len(overdue_milestones),
                "overdue_details": overdue_milestones,
            },
        }

        logger.info("project_report", project=project_id, progress=progress)
        return _truncate(json.dumps(report))

    def _list_projects(self, db: dict) -> str:
        projects = []
        for p in db["projects"].values():
            tasks = p.get("tasks", [])
            total = len(tasks)
            done = sum(1 for t in tasks if t.get("status") == "done")
            projects.append({
                "id": p["id"],
                "name": p["name"],
                "deadline": p.get("deadline", ""),
                "total_tasks": total,
                "completed_tasks": done,
                "progress_percent": round(done / total * 100, 1) if total > 0 else 0,
                "milestones_count": len(p.get("milestones", [])),
                "created_at": p.get("created_at", ""),
            })

        logger.info("projects_listed", count=len(projects))
        return _truncate(json.dumps({"projects": projects, "count": len(projects)}))
