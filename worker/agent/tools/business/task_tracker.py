"""Task tracker tool - create, manage, and visualize tasks with kanban view."""

import json
import os
import time
import uuid
from typing import Any

from agent.tools.base import BaseTool

TRACKER_FILE = "/tmp/whiteops_task_tracker.json"


class TaskTrackerTool(BaseTool):
    name = "task_tracker"
    description = (
        "Manage tasks and projects. Create tasks, update statuses, "
        "assign to team members, and view kanban-style board."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create_task", "list_tasks", "update_status", "assign", "kanban_view"],
                "description": "The task tracker action to perform",
            },
            "title": {
                "type": "string",
                "description": "Task title (for create_task)",
            },
            "description": {
                "type": "string",
                "description": "Task description",
            },
            "task_id": {
                "type": "string",
                "description": "Task ID (for update_status, assign)",
            },
            "status": {
                "type": "string",
                "enum": ["todo", "in_progress", "review", "done", "blocked"],
                "description": "Task status",
            },
            "assignee": {
                "type": "string",
                "description": "Person assigned to the task",
            },
            "priority": {
                "type": "string",
                "enum": ["low", "medium", "high", "critical"],
                "description": "Task priority (default: medium)",
            },
            "project": {
                "type": "string",
                "description": "Project name for grouping tasks",
            },
            "due_date": {
                "type": "string",
                "description": "Due date in YYYY-MM-DD format",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for the task",
            },
            "filter_status": {
                "type": "string",
                "enum": ["todo", "in_progress", "review", "done", "blocked", "all"],
                "description": "Filter tasks by status (for list_tasks, default: all)",
            },
            "filter_project": {
                "type": "string",
                "description": "Filter tasks by project (for list_tasks)",
            },
            "filter_assignee": {
                "type": "string",
                "description": "Filter tasks by assignee (for list_tasks)",
            },
        },
        "required": ["action"],
    }

    def _load_data(self) -> dict:
        if os.path.isfile(TRACKER_FILE):
            try:
                with open(TRACKER_FILE) as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError):
                pass
        return {"tasks": {}}

    def _save_data(self, data: dict) -> None:
        with open(TRACKER_FILE, "w") as f:
            json.dump(data, f, indent=2)

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]

        if action == "create_task":
            return self._create_task(kwargs)
        elif action == "list_tasks":
            return self._list_tasks(kwargs)
        elif action == "update_status":
            return self._update_status(kwargs)
        elif action == "assign":
            return self._assign(kwargs)
        elif action == "kanban_view":
            return self._kanban_view(kwargs)
        else:
            return json.dumps({"error": f"Unknown action: {action}"})

    def _create_task(self, kwargs: dict) -> str:
        title = kwargs.get("title")
        if not title:
            return json.dumps({"error": "title is required"})

        task_id = f"TASK-{str(uuid.uuid4())[:6].upper()}"
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        task = {
            "id": task_id,
            "title": title,
            "description": kwargs.get("description", ""),
            "status": kwargs.get("status", "todo"),
            "assignee": kwargs.get("assignee", ""),
            "priority": kwargs.get("priority", "medium"),
            "project": kwargs.get("project", "default"),
            "due_date": kwargs.get("due_date", ""),
            "tags": kwargs.get("tags", []),
            "created_at": now,
            "updated_at": now,
        }

        data = self._load_data()
        data["tasks"][task_id] = task
        self._save_data(data)

        return json.dumps({"success": True, "task": task})

    def _list_tasks(self, kwargs: dict) -> str:
        data = self._load_data()
        tasks = list(data["tasks"].values())

        # Apply filters
        filter_status = kwargs.get("filter_status", "all")
        if filter_status and filter_status != "all":
            tasks = [t for t in tasks if t["status"] == filter_status]

        filter_project = kwargs.get("filter_project")
        if filter_project:
            tasks = [t for t in tasks if t.get("project", "").lower() == filter_project.lower()]

        filter_assignee = kwargs.get("filter_assignee")
        if filter_assignee:
            tasks = [t for t in tasks if t.get("assignee", "").lower() == filter_assignee.lower()]

        # Sort by priority then by creation date
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        tasks.sort(key=lambda t: (priority_order.get(t.get("priority", "medium"), 2), t.get("created_at", "")))

        return json.dumps({"tasks": tasks, "count": len(tasks)})

    def _update_status(self, kwargs: dict) -> str:
        task_id = kwargs.get("task_id")
        status = kwargs.get("status")
        if not task_id or not status:
            return json.dumps({"error": "task_id and status are required"})

        data = self._load_data()
        task = data["tasks"].get(task_id)
        if not task:
            return json.dumps({"error": f"Task '{task_id}' not found"})

        old_status = task["status"]
        task["status"] = status
        task["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._save_data(data)

        return json.dumps({
            "success": True,
            "task_id": task_id,
            "old_status": old_status,
            "new_status": status,
        })

    def _assign(self, kwargs: dict) -> str:
        task_id = kwargs.get("task_id")
        assignee = kwargs.get("assignee")
        if not task_id or not assignee:
            return json.dumps({"error": "task_id and assignee are required"})

        data = self._load_data()
        task = data["tasks"].get(task_id)
        if not task:
            return json.dumps({"error": f"Task '{task_id}' not found"})

        old_assignee = task.get("assignee", "")
        task["assignee"] = assignee
        task["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._save_data(data)

        return json.dumps({
            "success": True,
            "task_id": task_id,
            "old_assignee": old_assignee,
            "new_assignee": assignee,
        })

    def _kanban_view(self, kwargs: dict) -> str:
        data = self._load_data()
        tasks = list(data["tasks"].values())

        filter_project = kwargs.get("filter_project")
        if filter_project:
            tasks = [t for t in tasks if t.get("project", "").lower() == filter_project.lower()]

        columns = {
            "todo": [],
            "in_progress": [],
            "review": [],
            "done": [],
            "blocked": [],
        }

        for task in tasks:
            status = task.get("status", "todo")
            if status in columns:
                columns[status].append({
                    "id": task["id"],
                    "title": task["title"],
                    "assignee": task.get("assignee", ""),
                    "priority": task.get("priority", "medium"),
                    "due_date": task.get("due_date", ""),
                })

        summary = {col: len(items) for col, items in columns.items()}

        return json.dumps({
            "kanban": columns,
            "summary": summary,
            "total": sum(summary.values()),
        })
