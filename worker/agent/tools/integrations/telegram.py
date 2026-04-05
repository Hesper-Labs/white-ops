"""Telegram Bot integration tool - send messages, documents, and get updates."""

import json
import os
from typing import Any

import httpx

from agent.tools.base import BaseTool


class TelegramTool(BaseTool):
    name = "telegram"
    description = (
        "Interact with Telegram via Bot API. Send messages and documents "
        "to chats, and retrieve recent updates."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["send_message", "send_document", "get_updates"],
                "description": "The Telegram action to perform",
            },
            "chat_id": {
                "type": "string",
                "description": "Telegram chat ID or @channel_username",
            },
            "text": {
                "type": "string",
                "description": "Message text to send",
            },
            "parse_mode": {
                "type": "string",
                "enum": ["HTML", "Markdown", "MarkdownV2"],
                "description": "Message parse mode (default: HTML)",
            },
            "document_url": {
                "type": "string",
                "description": "URL of document to send",
            },
            "document_path": {
                "type": "string",
                "description": "Local file path of document to send",
            },
            "caption": {
                "type": "string",
                "description": "Caption for the document",
            },
            "offset": {
                "type": "integer",
                "description": "Update offset for get_updates (for pagination)",
            },
            "limit": {
                "type": "integer",
                "description": "Max number of updates to retrieve (default 10, max 100)",
            },
        },
        "required": ["action"],
    }

    def _get_token(self) -> str:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        if not token:
            raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set")
        return token

    def _api_url(self, method: str) -> str:
        return f"https://api.telegram.org/bot{self._get_token()}/{method}"

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]

        try:
            if action == "send_message":
                return await self._send_message(kwargs)
            elif action == "send_document":
                return await self._send_document(kwargs)
            elif action == "get_updates":
                return await self._get_updates(kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except ValueError as e:
            return json.dumps({"error": str(e)})
        except httpx.HTTPError as e:
            return json.dumps({"error": f"Telegram API request failed: {e}"})

    async def _send_message(self, kwargs: dict) -> str:
        chat_id = kwargs.get("chat_id")
        text = kwargs.get("text")
        if not chat_id or not text:
            return json.dumps({"error": "chat_id and text are required"})

        payload: dict[str, Any] = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": kwargs.get("parse_mode", "HTML"),
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(self._api_url("sendMessage"), json=payload)
            data = resp.json()
            if data.get("ok"):
                msg = data["result"]
                return json.dumps({
                    "success": True,
                    "message_id": msg["message_id"],
                    "chat_id": msg["chat"]["id"],
                    "date": msg["date"],
                })
            return json.dumps({"error": data.get("description", "Unknown error")})

    async def _send_document(self, kwargs: dict) -> str:
        chat_id = kwargs.get("chat_id")
        if not chat_id:
            return json.dumps({"error": "chat_id is required"})

        document_url = kwargs.get("document_url")
        document_path = kwargs.get("document_path")

        if not document_url and not document_path:
            return json.dumps({"error": "document_url or document_path is required"})

        async with httpx.AsyncClient(timeout=30) as client:
            if document_url:
                # Send by URL
                payload: dict[str, Any] = {
                    "chat_id": chat_id,
                    "document": document_url,
                }
                if kwargs.get("caption"):
                    payload["caption"] = kwargs["caption"]

                resp = await client.post(self._api_url("sendDocument"), json=payload)
            else:
                # Send by file upload
                if not os.path.isfile(document_path):
                    return json.dumps({"error": f"File not found: {document_path}"})

                data: dict[str, Any] = {"chat_id": chat_id}
                if kwargs.get("caption"):
                    data["caption"] = kwargs["caption"]

                with open(document_path, "rb") as f:
                    files = {"document": (os.path.basename(document_path), f)}
                    resp = await client.post(
                        self._api_url("sendDocument"), data=data, files=files
                    )

            result = resp.json()
            if result.get("ok"):
                msg = result["result"]
                doc = msg.get("document", {})
                return json.dumps({
                    "success": True,
                    "message_id": msg["message_id"],
                    "file_name": doc.get("file_name", ""),
                    "file_size": doc.get("file_size", 0),
                })
            return json.dumps({"error": result.get("description", "Unknown error")})

    async def _get_updates(self, kwargs: dict) -> str:
        limit = min(kwargs.get("limit", 10), 100)
        params: dict[str, Any] = {"limit": limit}
        if kwargs.get("offset") is not None:
            params["offset"] = kwargs["offset"]

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(self._api_url("getUpdates"), params=params)
            data = resp.json()
            if not data.get("ok"):
                return json.dumps({"error": data.get("description", "Unknown error")})

            updates = []
            for update in data.get("result", []):
                entry: dict[str, Any] = {"update_id": update["update_id"]}
                msg = update.get("message") or update.get("edited_message")
                if msg:
                    entry["chat_id"] = msg["chat"]["id"]
                    entry["chat_title"] = msg["chat"].get("title", msg["chat"].get("username", ""))
                    entry["from"] = msg.get("from", {}).get("username", "unknown")
                    entry["text"] = msg.get("text", "")
                    entry["date"] = msg.get("date", 0)
                updates.append(entry)

            return json.dumps({"updates": updates, "count": len(updates)})
