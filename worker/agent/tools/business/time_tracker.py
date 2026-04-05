"""Time tracking tool - track time spent on tasks."""

import json
from pathlib import Path
from typing import Any
from datetime import datetime

from agent.tools.base import BaseTool

TIMESHEET_FILE = "/tmp/whiteops_timesheet.json"


class TimeTrackerTool(BaseTool):
    name = "time_tracker"
    description = (
        "Track time spent on tasks and projects. "
        "Start/stop timers, log hours, generate timesheet reports."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["start", "stop", "log", "report", "list"],
            },
            "task_name": {"type": "string"},
            "project": {"type": "string"},
            "hours": {"type": "number", "description": "Hours to log (for manual entry)"},
            "notes": {"type": "string"},
            "period": {"type": "string", "description": "Report period: today, week, month"},
        },
        "required": ["action"],
    }

    def _load(self) -> dict:
        if Path(TIMESHEET_FILE).exists():
            return json.loads(Path(TIMESHEET_FILE).read_text())
        return {"entries": [], "active_timer": None}

    def _save(self, data: dict) -> None:
        Path(TIMESHEET_FILE).write_text(json.dumps(data, indent=2))

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        db = self._load()

        if action == "start":
            if db["active_timer"]:
                return "Timer already running. Stop it first."
            db["active_timer"] = {
                "task": kwargs.get("task_name", "Untitled"),
                "project": kwargs.get("project", "General"),
                "started_at": datetime.now().isoformat(),
            }
            self._save(db)
            return f"Timer started: {db['active_timer']['task']}"

        elif action == "stop":
            if not db["active_timer"]:
                return "No active timer"
            start = datetime.fromisoformat(db["active_timer"]["started_at"])
            elapsed = (datetime.now() - start).total_seconds() / 3600
            entry = {
                "task": db["active_timer"]["task"],
                "project": db["active_timer"]["project"],
                "hours": round(elapsed, 2),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "notes": kwargs.get("notes", ""),
            }
            db["entries"].append(entry)
            db["active_timer"] = None
            self._save(db)
            return f"Timer stopped: {entry['task']} - {entry['hours']}h"

        elif action == "log":
            entry = {
                "task": kwargs.get("task_name", "Untitled"),
                "project": kwargs.get("project", "General"),
                "hours": kwargs.get("hours", 0),
                "date": datetime.now().strftime("%Y-%m-%d"),
                "notes": kwargs.get("notes", ""),
            }
            db["entries"].append(entry)
            self._save(db)
            return f"Logged: {entry['hours']}h on {entry['task']}"

        elif action == "report":
            total = sum(e.get("hours", 0) for e in db["entries"])
            by_project: dict[str, float] = {}
            for e in db["entries"]:
                proj = e.get("project", "General")
                by_project[proj] = by_project.get(proj, 0) + e.get("hours", 0)
            return json.dumps({
                "total_hours": round(total, 2),
                "total_entries": len(db["entries"]),
                "by_project": by_project,
                "active_timer": db["active_timer"],
            })

        elif action == "list":
            return json.dumps(db["entries"][-20:])

        return f"Unknown action: {action}"
