"""Notion integration tool - manage pages, databases, and search."""

import json
import os
from typing import Any

import httpx

from agent.tools.base import BaseTool


class NotionTool(BaseTool):
    name = "notion"
    description = (
        "Interact with Notion workspaces. Create and update pages, "
        "search content, list databases, and query database entries."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["create_page", "update_page", "search", "list_databases", "query_database"],
                "description": "The Notion action to perform",
            },
            "parent_id": {
                "type": "string",
                "description": "Parent page or database ID",
            },
            "page_id": {
                "type": "string",
                "description": "Page ID for update_page",
            },
            "database_id": {
                "type": "string",
                "description": "Database ID for query_database",
            },
            "title": {
                "type": "string",
                "description": "Page title",
            },
            "content": {
                "type": "string",
                "description": "Page content (plain text, will be converted to blocks)",
            },
            "properties": {
                "type": "object",
                "description": "Page properties (for database entries)",
            },
            "query": {
                "type": "string",
                "description": "Search query text",
            },
            "filter": {
                "type": "object",
                "description": "Database query filter object",
            },
            "sorts": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Database query sort options",
            },
            "page_size": {
                "type": "integer",
                "description": "Number of results (default 20, max 100)",
            },
        },
        "required": ["action"],
    }

    API_BASE = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"

    def _get_token(self) -> str:
        token = os.environ.get("NOTION_API_TOKEN", "")
        if not token:
            raise ValueError("NOTION_API_TOKEN environment variable is not set")
        return token

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._get_token()}",
            "Content-Type": "application/json",
            "Notion-Version": self.NOTION_VERSION,
        }

    def _text_to_blocks(self, text: str) -> list[dict]:
        """Convert plain text to Notion paragraph blocks."""
        blocks = []
        for paragraph in text.split("\n\n"):
            if paragraph.strip():
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": paragraph.strip()}}]
                    },
                })
        return blocks

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]

        try:
            if action == "create_page":
                return await self._create_page(kwargs)
            elif action == "update_page":
                return await self._update_page(kwargs)
            elif action == "search":
                return await self._search(kwargs)
            elif action == "list_databases":
                return await self._list_databases(kwargs)
            elif action == "query_database":
                return await self._query_database(kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except ValueError as e:
            return json.dumps({"error": str(e)})
        except httpx.HTTPError as e:
            return json.dumps({"error": f"Notion API request failed: {e}"})

    async def _create_page(self, kwargs: dict) -> str:
        parent_id = kwargs.get("parent_id")
        title = kwargs.get("title")
        if not parent_id or not title:
            return json.dumps({"error": "parent_id and title are required"})

        # Determine parent type (database or page)
        parent = {"database_id": parent_id} if kwargs.get("properties") else {"page_id": parent_id}

        payload: dict[str, Any] = {
            "parent": parent,
            "properties": kwargs.get("properties") or {
                "title": {
                    "title": [{"type": "text", "text": {"content": title}}]
                }
            },
        }

        if kwargs.get("content"):
            payload["children"] = self._text_to_blocks(kwargs["content"])

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.API_BASE}/pages",
                headers=self._headers(),
                json=payload,
            )
            if resp.status_code == 200:
                data = resp.json()
                return json.dumps({
                    "success": True,
                    "id": data["id"],
                    "url": data.get("url", ""),
                    "created_time": data.get("created_time", ""),
                })
            return json.dumps({"error": f"Status {resp.status_code}", "body": resp.text[:500]})

    async def _update_page(self, kwargs: dict) -> str:
        page_id = kwargs.get("page_id")
        if not page_id:
            return json.dumps({"error": "page_id is required"})

        payload: dict[str, Any] = {}
        if kwargs.get("properties"):
            payload["properties"] = kwargs["properties"]

        if not payload:
            return json.dumps({"error": "No properties provided to update"})

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.patch(
                f"{self.API_BASE}/pages/{page_id}",
                headers=self._headers(),
                json=payload,
            )
            if resp.status_code == 200:
                data = resp.json()
                return json.dumps({
                    "success": True,
                    "id": data["id"],
                    "last_edited_time": data.get("last_edited_time", ""),
                })
            return json.dumps({"error": f"Status {resp.status_code}", "body": resp.text[:500]})

    async def _search(self, kwargs: dict) -> str:
        query = kwargs.get("query", "")
        page_size = min(kwargs.get("page_size", 20), 100)

        payload: dict[str, Any] = {"page_size": page_size}
        if query:
            payload["query"] = query

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.API_BASE}/search",
                headers=self._headers(),
                json=payload,
            )
            if resp.status_code != 200:
                return json.dumps({"error": f"Status {resp.status_code}", "body": resp.text[:500]})

            data = resp.json()
            results = []
            for item in data.get("results", []):
                title = ""
                props = item.get("properties", {})
                if "title" in props:
                    title_parts = props["title"].get("title", [])
                    title = "".join(t.get("plain_text", "") for t in title_parts)
                elif "Name" in props:
                    name_parts = props["Name"].get("title", [])
                    title = "".join(t.get("plain_text", "") for t in name_parts)

                results.append({
                    "id": item["id"],
                    "type": item["object"],
                    "title": title,
                    "url": item.get("url", ""),
                    "last_edited": item.get("last_edited_time", ""),
                })
            return json.dumps({"results": results, "count": len(results)})

    async def _list_databases(self, kwargs: dict) -> str:
        page_size = min(kwargs.get("page_size", 20), 100)

        payload: dict[str, Any] = {
            "filter": {"value": "database", "property": "object"},
            "page_size": page_size,
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.API_BASE}/search",
                headers=self._headers(),
                json=payload,
            )
            if resp.status_code != 200:
                return json.dumps({"error": f"Status {resp.status_code}", "body": resp.text[:500]})

            data = resp.json()
            databases = []
            for db in data.get("results", []):
                title_parts = db.get("title", [])
                title = "".join(t.get("plain_text", "") for t in title_parts)
                databases.append({
                    "id": db["id"],
                    "title": title,
                    "url": db.get("url", ""),
                    "properties": list(db.get("properties", {}).keys()),
                })
            return json.dumps({"databases": databases, "count": len(databases)})

    async def _query_database(self, kwargs: dict) -> str:
        database_id = kwargs.get("database_id")
        if not database_id:
            return json.dumps({"error": "database_id is required"})

        page_size = min(kwargs.get("page_size", 20), 100)
        payload: dict[str, Any] = {"page_size": page_size}
        if kwargs.get("filter"):
            payload["filter"] = kwargs["filter"]
        if kwargs.get("sorts"):
            payload["sorts"] = kwargs["sorts"]

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.API_BASE}/databases/{database_id}/query",
                headers=self._headers(),
                json=payload,
            )
            if resp.status_code != 200:
                return json.dumps({"error": f"Status {resp.status_code}", "body": resp.text[:500]})

            data = resp.json()
            entries = []
            for page in data.get("results", []):
                entry: dict[str, Any] = {"id": page["id"], "url": page.get("url", "")}
                for prop_name, prop_val in page.get("properties", {}).items():
                    prop_type = prop_val.get("type", "")
                    if prop_type == "title":
                        entry[prop_name] = "".join(
                            t.get("plain_text", "") for t in prop_val.get("title", [])
                        )
                    elif prop_type == "rich_text":
                        entry[prop_name] = "".join(
                            t.get("plain_text", "") for t in prop_val.get("rich_text", [])
                        )
                    elif prop_type == "select":
                        sel = prop_val.get("select")
                        entry[prop_name] = sel.get("name", "") if sel else ""
                    elif prop_type == "number":
                        entry[prop_name] = prop_val.get("number")
                    elif prop_type == "checkbox":
                        entry[prop_name] = prop_val.get("checkbox")
                    elif prop_type == "date":
                        d = prop_val.get("date")
                        entry[prop_name] = d.get("start", "") if d else ""
                entries.append(entry)
            return json.dumps({"entries": entries, "count": len(entries), "has_more": data.get("has_more", False)})
