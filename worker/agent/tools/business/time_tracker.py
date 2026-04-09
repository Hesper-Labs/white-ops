"""Time tracker tool - track time spent on projects and tasks."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

STORAGE_PATH = "/tmp/whiteops_time.json"
MAX_OUTPUT_BYTES = 50 * 1024


def _truncate(result: str) -> str:
    if len(result) > MAX_OUTPUT_BYTES:
        return result[:MAX_OUTPUT_BYTES] + "\n... [output truncated at 50KB]"
    return result


class TimeTrackerTool(BaseTool):
    name = "time_tracker"
    description = (
        "Track time spent on projects and tasks. Start/stop timers with unique IDs, "
        "log time manually, generate reports with billable hours, and list active timers. "
        "Data stored in /tmp/whiteops_time.json."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["start_timer", "stop_timer", "log_time", "get_report", "list_active_timers"],
                "description": "Time tracking action.",
            },
            "project": {
                "type": "string",
                "description": "Project name.",
            },
            "task": {
                "type": "string",
                "description": "Task name.",
            },
            "description": {
                "type": "string",
                "description": "Description of the work.",
            },
            "timer_id": {
                "type": "string",
                "description": "Timer ID (for stop_timer).",
            },
            "hours": {
                "type": "number",
                "description": "Hours to log manually (for log_time).",
            },
            "date": {
                "type": "string",
                "description": "Date for time entry (YYYY-MM-DD, defaults to today).",
            },
            "start_date": {
                "type": "string",
                "description": "Report start date (YYYY-MM-DD).",
            },
            "end_date": {
                "type": "string",
                "description": "Report end date (YYYY-MM-DD).",
            },
            "billable": {
                "type": "boolean",
                "description": "Whether the time is billable (default: true).",
            },
            "hourly_rate": {
                "type": "number",
                "description": "Hourly rate for billing calculations.",
            },
        },
        "required": ["action"],
    }

    def _load(self) -> dict:
        path = Path(STORAGE_PATH)
        if path.exists():
            return json.loads(path.read_text())
        return {"timers": {}, "entries": [], "settings": {"default_hourly_rate": 0}}

    def _save(self, data: dict) -> None:
        Path(STORAGE_PATH).write_text(json.dumps(data, indent=2, ensure_ascii=False))

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "")
        logger.info("time_tracker_execute", action=action)

        try:
            db = self._load()

            if action == "start_timer":
                return self._start_timer(db, kwargs)
            elif action == "stop_timer":
                return self._stop_timer(db, kwargs)
            elif action == "log_time":
                return self._log_time(db, kwargs)
            elif action == "get_report":
                return self._get_report(db, kwargs)
            elif action == "list_active_timers":
                return self._list_active_timers(db)
            else:
                return _truncate(json.dumps({"error": f"Unknown action: {action}"}))
        except Exception as e:
            logger.error("time_tracker_failed", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"Time tracker failed: {e}"}))

    def _start_timer(self, db: dict, kwargs: dict) -> str:
        project = kwargs.get("project", "")
        task = kwargs.get("task", "")

        if not project:
            return _truncate(json.dumps({"error": "'project' is required"}))
        if not task:
            return _truncate(json.dumps({"error": "'task' is required"}))

        timer_id = uuid4().hex[:8]
        timer = {
            "id": timer_id,
            "project": project,
            "task": task,
            "description": kwargs.get("description", ""),
            "started_at": datetime.now().isoformat(),
            "billable": kwargs.get("billable", True),
        }

        db["timers"][timer_id] = timer
        self._save(db)

        logger.info("timer_started", id=timer_id, project=project, task=task)
        return _truncate(json.dumps({"success": True, "timer": timer}))

    def _stop_timer(self, db: dict, kwargs: dict) -> str:
        timer_id = kwargs.get("timer_id", "")
        if not timer_id:
            return _truncate(json.dumps({"error": "'timer_id' is required"}))

        if timer_id not in db["timers"]:
            return _truncate(json.dumps({"error": f"Timer {timer_id} not found"}))

        timer = db["timers"].pop(timer_id)
        start = datetime.fromisoformat(timer["started_at"])
        elapsed_hours = round((datetime.now() - start).total_seconds() / 3600, 4)

        entry = {
            "id": uuid4().hex[:8],
            "timer_id": timer_id,
            "project": timer["project"],
            "task": timer["task"],
            "description": timer.get("description", ""),
            "hours": round(elapsed_hours, 2),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "billable": timer.get("billable", True),
            "started_at": timer["started_at"],
            "stopped_at": datetime.now().isoformat(),
        }

        db["entries"].append(entry)
        self._save(db)

        logger.info("timer_stopped", id=timer_id, hours=entry["hours"])
        return _truncate(json.dumps({"success": True, "entry": entry}))

    def _log_time(self, db: dict, kwargs: dict) -> str:
        project = kwargs.get("project", "")
        task = kwargs.get("task", "")
        hours = kwargs.get("hours", 0)

        if not project:
            return _truncate(json.dumps({"error": "'project' is required"}))
        if not task:
            return _truncate(json.dumps({"error": "'task' is required"}))
        if hours <= 0:
            return _truncate(json.dumps({"error": "'hours' must be greater than 0"}))

        entry = {
            "id": uuid4().hex[:8],
            "project": project,
            "task": task,
            "description": kwargs.get("description", ""),
            "hours": round(hours, 2),
            "date": kwargs.get("date", datetime.now().strftime("%Y-%m-%d")),
            "billable": kwargs.get("billable", True),
            "manual": True,
        }

        db["entries"].append(entry)
        self._save(db)

        logger.info("time_logged", project=project, task=task, hours=hours)
        return _truncate(json.dumps({"success": True, "entry": entry}))

    def _get_report(self, db: dict, kwargs: dict) -> str:
        start_date = kwargs.get("start_date", "")
        end_date = kwargs.get("end_date", "")
        project_filter = kwargs.get("project", "")
        hourly_rate = kwargs.get("hourly_rate", db["settings"].get("default_hourly_rate", 0))

        if not start_date or not end_date:
            return _truncate(json.dumps({"error": "'start_date' and 'end_date' are required"}))

        entries = db["entries"]

        # Filter by date range
        entries = [e for e in entries if start_date <= e.get("date", "") <= end_date]

        # Filter by project
        if project_filter:
            entries = [e for e in entries if e.get("project", "").lower() == project_filter.lower()]

        # Calculate totals
        total_hours = 0
        billable_hours = 0
        by_project: dict[str, dict] = {}
        by_task: dict[str, float] = {}

        for e in entries:
            h = e.get("hours", 0)
            total_hours += h
            if e.get("billable", True):
                billable_hours += h

            proj = e.get("project", "General")
            if proj not in by_project:
                by_project[proj] = {"total_hours": 0, "billable_hours": 0, "entries": 0}
            by_project[proj]["total_hours"] += h
            by_project[proj]["entries"] += 1
            if e.get("billable", True):
                by_project[proj]["billable_hours"] += h

            task = f"{proj}/{e.get('task', 'Untitled')}"
            by_task[task] = by_task.get(task, 0) + h

        # Round values
        total_hours = round(total_hours, 2)
        billable_hours = round(billable_hours, 2)
        for p in by_project.values():
            p["total_hours"] = round(p["total_hours"], 2)
            p["billable_hours"] = round(p["billable_hours"], 2)
        by_task = {k: round(v, 2) for k, v in by_task.items()}

        report = {
            "period": {"start": start_date, "end": end_date},
            "total_hours": total_hours,
            "billable_hours": billable_hours,
            "non_billable_hours": round(total_hours - billable_hours, 2),
            "total_entries": len(entries),
            "by_project": by_project,
            "by_task": by_task,
        }

        if hourly_rate > 0:
            report["billing"] = {
                "hourly_rate": hourly_rate,
                "total_billable_amount": round(billable_hours * hourly_rate, 2),
                "currency": "USD",
            }

        logger.info("time_report", start=start_date, end=end_date, total_hours=total_hours)
        return _truncate(json.dumps(report))

    def _list_active_timers(self, db: dict) -> str:
        timers = list(db["timers"].values())

        # Calculate elapsed time for each active timer
        now = datetime.now()
        for timer in timers:
            start = datetime.fromisoformat(timer["started_at"])
            elapsed = (now - start).total_seconds() / 3600
            timer["elapsed_hours"] = round(elapsed, 2)

        logger.info("active_timers_listed", count=len(timers))
        return _truncate(json.dumps({"timers": timers, "count": len(timers)}))
