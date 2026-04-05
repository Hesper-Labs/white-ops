"""Internal email tool - send/receive emails between agents."""

import json
from typing import Any

import httpx

from agent.config import settings
from agent.tools.base import BaseTool


class InternalEmailTool(BaseTool):
    name = "internal_email"
    description = (
        "Send and receive emails to/from other agents within the White-Ops system. "
        "Each agent has an email address like agent-name@whiteops.local."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["send", "check_inbox", "read_message"],
            },
            "to": {"type": "string", "description": "Recipient agent email"},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "agent_id": {"type": "string", "description": "Your agent ID (for inbox)"},
            "message_id": {"type": "string", "description": "Message ID to read"},
        },
        "required": ["action"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]

        async with httpx.AsyncClient(base_url=settings.master_url, timeout=30) as client:
            if action == "send":
                response = await client.post(
                    "/api/v1/messages/send",
                    json={
                        "sender_agent_id": kwargs.get("agent_id", ""),
                        "recipient_agent_id": kwargs.get("to", ""),
                        "channel": "email",
                        "subject": kwargs.get("subject", ""),
                        "body": kwargs.get("body", ""),
                    },
                )
                return f"Email sent: {response.json()}"

            elif action == "check_inbox":
                response = await client.get(
                    "/api/v1/messages/",
                    params={"agent_id": kwargs.get("agent_id", ""), "channel": "email"},
                )
                return json.dumps(response.json())

            elif action == "read_message":
                message_id = kwargs.get("message_id", "")
                await client.patch(f"/api/v1/messages/{message_id}/read")
                return f"Message {message_id} marked as read"

        return f"Unknown action: {action}"
