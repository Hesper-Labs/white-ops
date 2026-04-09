"""Calendar tool - manage events via Google Calendar API."""

import json
import os
from typing import Any

import httpx
import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024


def _truncate(result: str) -> str:
    if len(result) > MAX_OUTPUT_BYTES:
        return result[:MAX_OUTPUT_BYTES] + "\n... [output truncated at 50KB]"
    return result


class CalendarTool(BaseTool):
    name = "calendar"
    description = (
        "Manage calendar events via Google Calendar API. Create, list, update, "
        "and delete events, and check attendee availability. "
        "Requires GOOGLE_CALENDAR_CREDENTIALS env var (JSON service account key)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "create_event",
                    "list_events",
                    "update_event",
                    "delete_event",
                    "check_availability",
                ],
                "description": "Calendar action to perform.",
            },
            "title": {
                "type": "string",
                "description": "Event title (for create_event).",
            },
            "start": {
                "type": "string",
                "description": "Start datetime in ISO 8601 format (e.g., 2024-01-15T09:00:00-05:00).",
            },
            "end": {
                "type": "string",
                "description": "End datetime in ISO 8601 format.",
            },
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of attendee email addresses.",
            },
            "description": {
                "type": "string",
                "description": "Event description.",
            },
            "location": {
                "type": "string",
                "description": "Event location.",
            },
            "start_date": {
                "type": "string",
                "description": "Start date for listing events (YYYY-MM-DD).",
            },
            "end_date": {
                "type": "string",
                "description": "End date for listing events (YYYY-MM-DD).",
            },
            "event_id": {
                "type": "string",
                "description": "Event ID (for update_event, delete_event).",
            },
            "updates": {
                "type": "object",
                "description": "Fields to update on an event (title, start, end, description, location, attendees).",
            },
            "calendar_id": {
                "type": "string",
                "description": "Calendar ID (defaults to 'primary').",
            },
        },
        "required": ["action"],
    }

    API_BASE = "https://www.googleapis.com/calendar/v3"

    def _get_credentials(self) -> str:
        """Get the access token from environment credentials."""
        creds = os.environ.get("GOOGLE_CALENDAR_CREDENTIALS", "")
        if not creds:
            raise ValueError(
                "GOOGLE_CALENDAR_CREDENTIALS environment variable is required. "
                "Set it to a valid Google OAuth2 access token or service account JSON."
            )
        return creds

    def _get_headers(self) -> dict[str, str]:
        """Build authorization headers."""
        creds = self._get_credentials()
        # Support both raw token and JSON credentials
        try:
            creds_data = json.loads(creds)
            token = creds_data.get("access_token", creds_data.get("token", ""))
        except (json.JSONDecodeError, TypeError):
            token = creds  # Assume it's a raw token

        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "")
        calendar_id = kwargs.get("calendar_id", "primary")
        logger.info("calendar_tool_execute", action=action)

        try:
            headers = self._get_headers()
        except ValueError as e:
            logger.error("calendar_config_error", error=str(e))
            return _truncate(json.dumps({"error": str(e)}))

        try:
            if action == "create_event":
                return await self._create_event(kwargs, headers, calendar_id)
            elif action == "list_events":
                return await self._list_events(kwargs, headers, calendar_id)
            elif action == "update_event":
                return await self._update_event(kwargs, headers, calendar_id)
            elif action == "delete_event":
                return await self._delete_event(kwargs, headers, calendar_id)
            elif action == "check_availability":
                return await self._check_availability(kwargs, headers)
            else:
                return _truncate(json.dumps({"error": f"Unknown action: {action}"}))
        except httpx.HTTPError as e:
            logger.error("calendar_api_error", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"Google Calendar API error: {e}"}))
        except Exception as e:
            logger.error("calendar_error", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"Calendar operation failed: {e}"}))

    async def _create_event(self, kwargs: dict, headers: dict, calendar_id: str) -> str:
        title = kwargs.get("title", "")
        start = kwargs.get("start", "")
        end = kwargs.get("end", "")

        if not title:
            return _truncate(json.dumps({"error": "'title' is required"}))
        if not start or not end:
            return _truncate(json.dumps({"error": "'start' and 'end' are required"}))

        event_body: dict[str, Any] = {
            "summary": title,
            "start": {"dateTime": start},
            "end": {"dateTime": end},
        }

        if kwargs.get("description"):
            event_body["description"] = kwargs["description"]
        if kwargs.get("location"):
            event_body["location"] = kwargs["location"]
        if kwargs.get("attendees"):
            event_body["attendees"] = [{"email": email} for email in kwargs["attendees"]]

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.API_BASE}/calendars/{calendar_id}/events",
                headers=headers,
                json=event_body,
            )

            if resp.status_code in (200, 201):
                data = resp.json()
                logger.info("calendar_event_created", event_id=data.get("id"))
                return _truncate(json.dumps({
                    "success": True,
                    "event_id": data.get("id", ""),
                    "html_link": data.get("htmlLink", ""),
                    "summary": data.get("summary", ""),
                    "start": data.get("start", {}),
                    "end": data.get("end", {}),
                    "status": data.get("status", ""),
                }))
            else:
                return _truncate(json.dumps({
                    "error": f"Failed to create event (status {resp.status_code})",
                    "details": resp.text[:500],
                }))

    async def _list_events(self, kwargs: dict, headers: dict, calendar_id: str) -> str:
        start_date = kwargs.get("start_date", "")
        end_date = kwargs.get("end_date", "")

        if not start_date or not end_date:
            return _truncate(json.dumps({"error": "'start_date' and 'end_date' are required"}))

        params: dict[str, Any] = {
            "timeMin": f"{start_date}T00:00:00Z",
            "timeMax": f"{end_date}T23:59:59Z",
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": 100,
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.API_BASE}/calendars/{calendar_id}/events",
                headers=headers,
                params=params,
            )

            if resp.status_code == 200:
                data = resp.json()
                events = []
                for item in data.get("items", []):
                    events.append({
                        "id": item.get("id", ""),
                        "summary": item.get("summary", ""),
                        "start": item.get("start", {}),
                        "end": item.get("end", {}),
                        "location": item.get("location", ""),
                        "description": item.get("description", "")[:200],
                        "attendees": [
                            a.get("email", "") for a in item.get("attendees", [])
                        ],
                        "status": item.get("status", ""),
                    })
                logger.info("calendar_events_listed", count=len(events))
                return _truncate(json.dumps({"events": events, "count": len(events)}))
            else:
                return _truncate(json.dumps({
                    "error": f"Failed to list events (status {resp.status_code})",
                    "details": resp.text[:500],
                }))

    async def _update_event(self, kwargs: dict, headers: dict, calendar_id: str) -> str:
        event_id = kwargs.get("event_id", "")
        updates = kwargs.get("updates", {})

        if not event_id:
            return _truncate(json.dumps({"error": "'event_id' is required"}))
        if not updates:
            return _truncate(json.dumps({"error": "'updates' object is required"}))

        patch_body: dict[str, Any] = {}
        if "title" in updates:
            patch_body["summary"] = updates["title"]
        if "start" in updates:
            patch_body["start"] = {"dateTime": updates["start"]}
        if "end" in updates:
            patch_body["end"] = {"dateTime": updates["end"]}
        if "description" in updates:
            patch_body["description"] = updates["description"]
        if "location" in updates:
            patch_body["location"] = updates["location"]
        if "attendees" in updates:
            patch_body["attendees"] = [{"email": e} for e in updates["attendees"]]

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.patch(
                f"{self.API_BASE}/calendars/{calendar_id}/events/{event_id}",
                headers=headers,
                json=patch_body,
            )

            if resp.status_code == 200:
                data = resp.json()
                logger.info("calendar_event_updated", event_id=event_id)
                return _truncate(json.dumps({
                    "success": True,
                    "event_id": data.get("id", ""),
                    "summary": data.get("summary", ""),
                    "updated": data.get("updated", ""),
                }))
            else:
                return _truncate(json.dumps({
                    "error": f"Failed to update event (status {resp.status_code})",
                    "details": resp.text[:500],
                }))

    async def _delete_event(self, kwargs: dict, headers: dict, calendar_id: str) -> str:
        event_id = kwargs.get("event_id", "")
        if not event_id:
            return _truncate(json.dumps({"error": "'event_id' is required"}))

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(
                f"{self.API_BASE}/calendars/{calendar_id}/events/{event_id}",
                headers=headers,
            )

            if resp.status_code in (200, 204):
                logger.info("calendar_event_deleted", event_id=event_id)
                return _truncate(json.dumps({
                    "success": True,
                    "message": f"Event {event_id} deleted",
                }))
            else:
                return _truncate(json.dumps({
                    "error": f"Failed to delete event (status {resp.status_code})",
                    "details": resp.text[:500],
                }))

    async def _check_availability(self, kwargs: dict, headers: dict) -> str:
        attendees = kwargs.get("attendees", [])
        start = kwargs.get("start", "")
        end = kwargs.get("end", "")

        if not attendees:
            return _truncate(json.dumps({"error": "'attendees' list is required"}))
        if not start or not end:
            return _truncate(json.dumps({"error": "'start' and 'end' are required"}))

        freebusy_body = {
            "timeMin": start,
            "timeMax": end,
            "items": [{"id": email} for email in attendees],
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.API_BASE}/freeBusy",
                headers=headers,
                json=freebusy_body,
            )

            if resp.status_code == 200:
                data = resp.json()
                calendars = data.get("calendars", {})
                availability = {}
                all_available = True

                for email in attendees:
                    cal_data = calendars.get(email, {})
                    busy_slots = cal_data.get("busy", [])
                    is_available = len(busy_slots) == 0
                    if not is_available:
                        all_available = False
                    availability[email] = {
                        "available": is_available,
                        "busy_slots": busy_slots,
                    }

                logger.info("calendar_availability_checked", attendees=len(attendees), all_available=all_available)
                return _truncate(json.dumps({
                    "all_available": all_available,
                    "time_range": {"start": start, "end": end},
                    "availability": availability,
                }))
            else:
                return _truncate(json.dumps({
                    "error": f"Failed to check availability (status {resp.status_code})",
                    "details": resp.text[:500],
                }))
