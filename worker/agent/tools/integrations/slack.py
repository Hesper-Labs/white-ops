"""Slack integration tool - send messages, list channels, read messages."""

import json
import os
from typing import Any

import httpx

from agent.tools.base import BaseTool


class SlackTool(BaseTool):
    name = "slack"
    description = (
        "Interact with Slack workspaces. Send messages to channels, "
        "list available channels, and read recent messages from channels."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["send_message", "list_channels", "read_messages"],
                "description": "The Slack action to perform",
            },
            "channel": {
                "type": "string",
                "description": "Channel name or ID (required for send_message, read_messages)",
            },
            "text": {
                "type": "string",
                "description": "Message text to send (required for send_message)",
            },
            "limit": {
                "type": "integer",
                "description": "Number of messages to read (default 10, max 100)",
            },
        },
        "required": ["action"],
    }

    SLACK_API = "https://slack.com/api"

    def _get_token(self) -> str:
        token = os.environ.get("SLACK_BOT_TOKEN", "")
        if not token:
            raise ValueError("SLACK_BOT_TOKEN environment variable is not set")
        return token

    def _get_webhook_url(self) -> str:
        url = os.environ.get("SLACK_WEBHOOK_URL", "")
        if not url:
            raise ValueError("SLACK_WEBHOOK_URL environment variable is not set")
        return url

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json; charset=utf-8",
        }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]

        try:
            if action == "send_message":
                return await self._send_message(kwargs)
            elif action == "list_channels":
                return await self._list_channels()
            elif action == "read_messages":
                return await self._read_messages(kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except ValueError as e:
            return json.dumps({"error": str(e)})
        except httpx.HTTPError as e:
            return json.dumps({"error": f"Slack API request failed: {e}"})

    async def _send_message(self, kwargs: dict) -> str:
        channel = kwargs.get("channel")
        text = kwargs.get("text")
        if not channel or not text:
            return json.dumps({"error": "channel and text are required for send_message"})

        # Try Bot API first, fall back to webhook
        try:
            token = self._get_token()
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.SLACK_API}/chat.postMessage",
                    headers=self._headers(),
                    json={"channel": channel, "text": text},
                )
                data = resp.json()
                if data.get("ok"):
                    return json.dumps({
                        "success": True,
                        "channel": data.get("channel"),
                        "ts": data.get("ts"),
                    })
                return json.dumps({"error": data.get("error", "Unknown Slack error")})
        except ValueError:
            # No bot token, try webhook
            webhook_url = self._get_webhook_url()
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    webhook_url,
                    json={"channel": channel, "text": text},
                )
                if resp.status_code == 200:
                    return json.dumps({"success": True, "method": "webhook"})
                return json.dumps({"error": f"Webhook returned status {resp.status_code}"})

    async def _list_channels(self) -> str:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.SLACK_API}/conversations.list",
                headers=self._headers(),
                params={"types": "public_channel,private_channel", "limit": 200},
            )
            data = resp.json()
            if not data.get("ok"):
                return json.dumps({"error": data.get("error", "Failed to list channels")})

            channels = [
                {
                    "id": ch["id"],
                    "name": ch["name"],
                    "topic": ch.get("topic", {}).get("value", ""),
                    "num_members": ch.get("num_members", 0),
                }
                for ch in data.get("channels", [])
            ]
            return json.dumps({"channels": channels, "count": len(channels)})

    async def _read_messages(self, kwargs: dict) -> str:
        channel = kwargs.get("channel")
        if not channel:
            return json.dumps({"error": "channel is required for read_messages"})

        limit = min(kwargs.get("limit", 10), 100)

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.SLACK_API}/conversations.history",
                headers=self._headers(),
                params={"channel": channel, "limit": limit},
            )
            data = resp.json()
            if not data.get("ok"):
                return json.dumps({"error": data.get("error", "Failed to read messages")})

            messages = [
                {
                    "user": msg.get("user", "unknown"),
                    "text": msg.get("text", ""),
                    "ts": msg.get("ts", ""),
                    "type": msg.get("type", ""),
                }
                for msg in data.get("messages", [])
            ]
            return json.dumps({"messages": messages, "count": len(messages)})
