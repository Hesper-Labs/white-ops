"""Calendar tool - manage events, meetings, and reminders."""

import json
from pathlib import Path
from typing import Any
from datetime import datetime, timedelta

from agent.tools.base import BaseTool

CALENDAR_FILE = "/tmp/whiteops_calendar.json"


class CalendarTool(BaseTool):
    name = "calendar"
    description = (
        "Manage calendar events, meetings, and reminders. "
        "Create, list, update, and check for scheduling conflicts."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create", "list", "today", "upcoming", "delete", "check_conflicts"],
            },
            "title": {"type": "string"},
            "start": {"type": "string", "description": "Start datetime (ISO format)"},
            "end": {"type": "string", "description": "End datetime (ISO format)"},
            "description": {"type": "string"},
            "attendees": {"type": "array", "items": {"type": "string"}},
            "recurring": {"type": "string", "enum": ["none", "daily", "weekly", "monthly"]},
            "event_id": {"type": "string"},
        },
        "required": ["action"],
    }

    def _load(self) -> list:
        if Path(CALENDAR_FILE).exists():
            return json.loads(Path(CALENDAR_FILE).read_text())
        return []

    def _save(self, events: list) -> None:
        Path(CALENDAR_FILE).write_text(json.dumps(events, indent=2))

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        events = self._load()

        if action == "create":
            import uuid
            event = {
                "id": str(uuid.uuid4())[:8],
                "title": kwargs.get("title", "Untitled"),
                "start": kwargs.get("start", datetime.now().isoformat()),
                "end": kwargs.get("end", ""),
                "description": kwargs.get("description", ""),
                "attendees": kwargs.get("attendees", []),
                "recurring": kwargs.get("recurring", "none"),
                "created_at": datetime.now().isoformat(),
            }
            events.append(event)
            self._save(events)
            return json.dumps({"id": event["id"], "title": event["title"], "start": event["start"]})

        elif action == "list":
            return json.dumps(events[-30:])

        elif action == "today":
            today = datetime.now().strftime("%Y-%m-%d")
            todays = [e for e in events if e.get("start", "").startswith(today)]
            return json.dumps(todays)

        elif action == "upcoming":
            now = datetime.now().isoformat()
            upcoming = [e for e in events if e.get("start", "") >= now]
            upcoming.sort(key=lambda e: e.get("start", ""))
            return json.dumps(upcoming[:10])

        elif action == "delete":
            eid = kwargs.get("event_id", "")
            events = [e for e in events if e.get("id") != eid]
            self._save(events)
            return f"Event {eid} deleted"

        elif action == "check_conflicts":
            start = kwargs.get("start", "")
            end = kwargs.get("end", "")
            conflicts = []
            for e in events:
                estart = e.get("start", "")
                eend = e.get("end", estart)
                if estart and start and end:
                    if estart < end and eend > start:
                        conflicts.append(e)
            return json.dumps({"has_conflicts": len(conflicts) > 0, "conflicts": conflicts})

        return f"Unknown action: {action}"
