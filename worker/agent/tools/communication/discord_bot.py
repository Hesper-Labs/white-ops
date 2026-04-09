"""Discord Bot tool - send messages and embeds via Discord Bot API."""

import json
import os
from typing import Any

import httpx
import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
DISCORD_API_BASE = "https://discord.com/api/v10"


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_BYTES:
        return text[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
    return text


class DiscordBotTool(BaseTool):
    name = "discord_bot"
    description = (
        "Interact with Discord via the Bot API. Send messages, create rich embeds, "
        "and list channels in a guild. Requires DISCORD_BOT_TOKEN env var."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["send_message", "create_embed", "list_channels"],
                "description": "Action to perform.",
            },
            "channel_id": {
                "type": "string",
                "description": "Discord channel ID (required for send_message, create_embed).",
            },
            "content": {
                "type": "string",
                "description": "Plain text message content.",
            },
            "embed": {
                "type": "object",
                "description": "Discord embed object (optional for send_message).",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "color": {"type": "integer"},
                    "fields": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "value": {"type": "string"},
                                "inline": {"type": "boolean"},
                            },
                        },
                    },
                },
            },
            "title": {
                "type": "string",
                "description": "Embed title (for create_embed).",
            },
            "description": {
                "type": "string",
                "description": "Embed description (for create_embed).",
            },
            "fields": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "value": {"type": "string"},
                        "inline": {"type": "boolean"},
                    },
                },
                "description": "Embed fields (for create_embed).",
            },
            "color": {
                "type": "integer",
                "description": "Embed color as integer (for create_embed).",
            },
            "guild_id": {
                "type": "string",
                "description": "Guild/server ID (required for list_channels).",
            },
        },
        "required": ["action"],
    }

    def _get_token(self) -> str | None:
        return os.environ.get("DISCORD_BOT_TOKEN")

    def _headers(self, token: str) -> dict:
        return {
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
        }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action")
        logger.info("discord_tool_execute", action=action)

        token = self._get_token()
        if not token:
            return json.dumps({"error": "DISCORD_BOT_TOKEN environment variable not set"})

        try:
            if action == "send_message":
                return await self._send_message(kwargs, token)
            elif action == "create_embed":
                return await self._create_embed(kwargs, token)
            elif action == "list_channels":
                return await self._list_channels(kwargs, token)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except httpx.TimeoutException:
            logger.error("discord_timeout", action=action)
            return json.dumps({"error": "Request timed out after 30 seconds"})
        except httpx.HTTPStatusError as e:
            logger.error("discord_http_error", status=e.response.status_code)
            return json.dumps({"error": f"HTTP {e.response.status_code}: {e.response.text[:500]}"})
        except Exception as e:
            logger.error("discord_error", error=str(e))
            return json.dumps({"error": f"Discord operation failed: {e}"})

    async def _send_message(self, kwargs: dict, token: str) -> str:
        channel_id = kwargs.get("channel_id")
        if not channel_id:
            return json.dumps({"error": "channel_id is required"})

        content = kwargs.get("content")
        embed = kwargs.get("embed")

        if not content and not embed:
            return json.dumps({"error": "Either content or embed is required"})

        payload: dict[str, Any] = {}
        if content:
            payload["content"] = content[:2000]  # Discord limit
        if embed:
            payload["embeds"] = [embed]

        url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=self._headers(token), json=payload)
            resp.raise_for_status()
            data = resp.json()

        logger.info("discord_message_sent", channel_id=channel_id, message_id=data.get("id"))
        return json.dumps({
            "success": True,
            "message_id": data.get("id"),
            "channel_id": channel_id,
        })

    async def _create_embed(self, kwargs: dict, token: str) -> str:
        channel_id = kwargs.get("channel_id")
        if not channel_id:
            return json.dumps({"error": "channel_id is required"})

        title = kwargs.get("title", "")
        description = kwargs.get("description", "")
        fields = kwargs.get("fields", [])
        color = kwargs.get("color", 0x5865F2)  # Discord blurple

        if not title and not description:
            return json.dumps({"error": "title or description is required for embed"})

        embed: dict[str, Any] = {}
        if title:
            embed["title"] = title[:256]
        if description:
            embed["description"] = description[:4096]
        if color:
            embed["color"] = color

        if fields:
            embed["fields"] = [
                {
                    "name": f.get("name", "")[:256],
                    "value": f.get("value", "")[:1024],
                    "inline": f.get("inline", False),
                }
                for f in fields[:25]  # Discord limit: 25 fields
            ]

        payload = {"embeds": [embed]}

        url = f"{DISCORD_API_BASE}/channels/{channel_id}/messages"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=self._headers(token), json=payload)
            resp.raise_for_status()
            data = resp.json()

        logger.info("discord_embed_sent", channel_id=channel_id, title=title)
        return json.dumps({
            "success": True,
            "message_id": data.get("id"),
            "channel_id": channel_id,
        })

    async def _list_channels(self, kwargs: dict, token: str) -> str:
        guild_id = kwargs.get("guild_id")
        if not guild_id:
            return json.dumps({"error": "guild_id is required"})

        url = f"{DISCORD_API_BASE}/guilds/{guild_id}/channels"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=self._headers(token))
            resp.raise_for_status()
            data = resp.json()

        channels = [
            {
                "id": ch.get("id"),
                "name": ch.get("name"),
                "type": ch.get("type"),
                "topic": ch.get("topic", ""),
                "position": ch.get("position"),
            }
            for ch in data
        ]

        logger.info("discord_channels_listed", guild_id=guild_id, count=len(channels))
        return _truncate(json.dumps({"channels": channels, "count": len(channels)}))
