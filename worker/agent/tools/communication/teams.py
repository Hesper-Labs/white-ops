"""Microsoft Teams tool - send messages and cards via Teams webhooks."""

import json
from typing import Any

import httpx
import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024  # 50KB


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_BYTES:
        return text[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
    return text


class TeamsTool(BaseTool):
    name = "teams"
    description = (
        "Send messages and adaptive cards to Microsoft Teams channels via "
        "Incoming Webhooks or interact with the MS Graph API for channel listing."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["send_message", "create_card", "list_channels"],
                "description": "Action to perform.",
            },
            "webhook_url": {
                "type": "string",
                "description": "Teams Incoming Webhook URL (required for send_message, create_card).",
            },
            "message": {
                "type": "string",
                "description": "Plain text message to send.",
            },
            "title": {
                "type": "string",
                "description": "Title for the message or card.",
            },
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "facts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "value": {"type": "string"},
                                },
                            },
                        },
                        "text": {"type": "string"},
                    },
                },
                "description": "Card sections with title, facts, and text.",
            },
            "graph_token": {
                "type": "string",
                "description": "MS Graph API bearer token (required for list_channels).",
            },
            "team_id": {
                "type": "string",
                "description": "Team ID for list_channels.",
            },
        },
        "required": ["action"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action")
        logger.info("teams_tool_execute", action=action)

        try:
            if action == "send_message":
                return await self._send_message(kwargs)
            elif action == "create_card":
                return await self._create_card(kwargs)
            elif action == "list_channels":
                return await self._list_channels(kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except httpx.TimeoutException:
            logger.error("teams_timeout", action=action)
            return json.dumps({"error": "Request timed out after 30 seconds"})
        except httpx.HTTPStatusError as e:
            logger.error("teams_http_error", status=e.response.status_code)
            return json.dumps({"error": f"HTTP {e.response.status_code}: {e.response.text[:500]}"})
        except Exception as e:
            logger.error("teams_error", error=str(e))
            return json.dumps({"error": f"Teams operation failed: {e}"})

    async def _send_message(self, kwargs: dict) -> str:
        webhook_url = kwargs.get("webhook_url")
        if not webhook_url:
            return json.dumps({"error": "webhook_url is required for send_message"})

        message = kwargs.get("message", "")
        title = kwargs.get("title")
        if not message:
            return json.dumps({"error": "message is required"})

        # Build AdaptiveCard payload
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [],
                    },
                }
            ],
        }

        body = card["attachments"][0]["content"]["body"]
        if title:
            body.append({
                "type": "TextBlock",
                "text": title,
                "weight": "Bolder",
                "size": "Medium",
            })
        body.append({
            "type": "TextBlock",
            "text": message,
            "wrap": True,
        })

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(webhook_url, json=card)
            resp.raise_for_status()

        logger.info("teams_message_sent", title=title)
        return json.dumps({"success": True, "message": "Message sent to Teams"})

    async def _create_card(self, kwargs: dict) -> str:
        webhook_url = kwargs.get("webhook_url")
        if not webhook_url:
            return json.dumps({"error": "webhook_url is required for create_card"})

        title = kwargs.get("title", "Notification")
        sections = kwargs.get("sections", [])

        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "text": title,
                                "weight": "Bolder",
                                "size": "Large",
                            }
                        ],
                    },
                }
            ],
        }

        body = card["attachments"][0]["content"]["body"]

        for section in sections:
            if section.get("title"):
                body.append({
                    "type": "TextBlock",
                    "text": section["title"],
                    "weight": "Bolder",
                    "size": "Medium",
                    "separator": True,
                })
            if section.get("text"):
                body.append({
                    "type": "TextBlock",
                    "text": section["text"],
                    "wrap": True,
                })
            if section.get("facts"):
                fact_set = {"type": "FactSet", "facts": []}
                for fact in section["facts"]:
                    fact_set["facts"].append({
                        "title": fact.get("name", ""),
                        "value": fact.get("value", ""),
                    })
                body.append(fact_set)

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(webhook_url, json=card)
            resp.raise_for_status()

        logger.info("teams_card_sent", title=title, sections=len(sections))
        return json.dumps({"success": True, "message": f"Card '{title}' sent to Teams"})

    async def _list_channels(self, kwargs: dict) -> str:
        graph_token = kwargs.get("graph_token")
        team_id = kwargs.get("team_id")

        if not graph_token:
            return json.dumps({"error": "graph_token (MS Graph API token) is required"})
        if not team_id:
            return json.dumps({"error": "team_id is required"})

        url = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels"
        headers = {"Authorization": f"Bearer {graph_token}"}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        channels = [
            {
                "id": ch.get("id"),
                "name": ch.get("displayName"),
                "description": ch.get("description", ""),
                "membership_type": ch.get("membershipType", ""),
            }
            for ch in data.get("value", [])
        ]

        logger.info("teams_channels_listed", team_id=team_id, count=len(channels))
        return _truncate(json.dumps({"channels": channels, "count": len(channels)}))
