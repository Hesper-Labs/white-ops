"""Notion integration tool - manage pages, databases, and search via Notion API."""

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


class NotionTool(BaseTool):
    name = "notion"
    description = (
        "Interact with Notion workspaces via the Notion API. Search content, "
        "get and create pages, update page properties, get database schemas, "
        "and query databases with filters and sorts. "
        "Requires NOTION_API_KEY env var. Uses Notion-Version: 2022-06-28."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "search",
                    "get_page",
                    "create_page",
                    "update_page",
                    "get_database",
                    "query_database",
                ],
                "description": "Notion action to perform.",
            },
            "query": {
                "type": "string",
                "description": "Search query text (for search).",
            },
            "page_id": {
                "type": "string",
                "description": "Page ID (for get_page, update_page).",
            },
            "parent_id": {
                "type": "string",
                "description": "Parent page or database ID (for create_page).",
            },
            "title": {
                "type": "string",
                "description": "Page title (for create_page).",
            },
            "content": {
                "type": "string",
                "description": "Page content as plain text (for create_page).",
            },
            "properties": {
                "type": "object",
                "description": "Page properties to set or update.",
            },
            "database_id": {
                "type": "string",
                "description": "Database ID (for get_database, query_database).",
            },
            "filter": {
                "type": "object",
                "description": "Notion database filter object.",
            },
            "sort": {
                "type": "array",
                "items": {"type": "object"},
                "description": "Notion database sort options.",
            },
            "page_size": {
                "type": "integer",
                "description": "Number of results to return (default 20, max 100).",
            },
        },
        "required": ["action"],
    }

    API_BASE = "https://api.notion.com/v1"
    NOTION_VERSION = "2022-06-28"

    def _get_headers(self) -> dict[str, str]:
        """Get API headers with authentication."""
        api_key = os.environ.get("NOTION_API_KEY", "")
        if not api_key:
            raise ValueError("NOTION_API_KEY environment variable is required")
        return {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Notion-Version": self.NOTION_VERSION,
        }

    def _text_to_blocks(self, text: str) -> list[dict]:
        """Convert plain text to Notion paragraph blocks."""
        blocks = []
        for paragraph in text.split("\n\n"):
            stripped = paragraph.strip()
            if stripped:
                blocks.append({
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": [{"type": "text", "text": {"content": stripped}}]
                    },
                })
        return blocks

    def _extract_title(self, properties: dict) -> str:
        """Extract title from Notion page properties."""
        for prop_name in ("title", "Title", "Name", "name"):
            if prop_name in properties:
                prop = properties[prop_name]
                if prop.get("type") == "title":
                    return "".join(
                        t.get("plain_text", "") for t in prop.get("title", [])
                    )
        return ""

    def _extract_property_value(self, prop: dict) -> Any:
        """Extract a human-readable value from a Notion property."""
        prop_type = prop.get("type", "")

        if prop_type == "title":
            return "".join(t.get("plain_text", "") for t in prop.get("title", []))
        elif prop_type == "rich_text":
            return "".join(t.get("plain_text", "") for t in prop.get("rich_text", []))
        elif prop_type == "select":
            sel = prop.get("select")
            return sel.get("name", "") if sel else ""
        elif prop_type == "multi_select":
            return [s.get("name", "") for s in prop.get("multi_select", [])]
        elif prop_type == "number":
            return prop.get("number")
        elif prop_type == "checkbox":
            return prop.get("checkbox")
        elif prop_type == "date":
            d = prop.get("date")
            return {"start": d.get("start", ""), "end": d.get("end")} if d else None
        elif prop_type == "email":
            return prop.get("email")
        elif prop_type == "url":
            return prop.get("url")
        elif prop_type == "phone_number":
            return prop.get("phone_number")
        elif prop_type == "status":
            status = prop.get("status")
            return status.get("name", "") if status else ""
        elif prop_type == "people":
            return [p.get("name", p.get("id", "")) for p in prop.get("people", [])]
        elif prop_type == "relation":
            return [r.get("id", "") for r in prop.get("relation", [])]
        else:
            return f"<{prop_type}>"

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "")
        logger.info("notion_execute", action=action)

        try:
            headers = self._get_headers()
        except ValueError as e:
            return _truncate(json.dumps({"error": str(e)}))

        try:
            if action == "search":
                return await self._search(kwargs, headers)
            elif action == "get_page":
                return await self._get_page(kwargs, headers)
            elif action == "create_page":
                return await self._create_page(kwargs, headers)
            elif action == "update_page":
                return await self._update_page(kwargs, headers)
            elif action == "get_database":
                return await self._get_database(kwargs, headers)
            elif action == "query_database":
                return await self._query_database(kwargs, headers)
            else:
                return _truncate(json.dumps({"error": f"Unknown action: {action}"}))
        except httpx.HTTPError as e:
            logger.error("notion_api_error", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"Notion API error: {e}"}))
        except Exception as e:
            logger.error("notion_failed", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"Notion operation failed: {e}"}))

    async def _search(self, kwargs: dict, headers: dict) -> str:
        query = kwargs.get("query", "")
        page_size = min(kwargs.get("page_size", 20), 100)

        payload: dict[str, Any] = {"page_size": page_size}
        if query:
            payload["query"] = query

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.API_BASE}/search",
                headers=headers,
                json=payload,
            )

            if resp.status_code != 200:
                return _truncate(json.dumps({
                    "error": f"Search failed (status {resp.status_code})",
                    "details": resp.text[:500],
                }))

            data = resp.json()
            results = []
            for item in data.get("results", []):
                title = self._extract_title(item.get("properties", {}))
                results.append({
                    "id": item["id"],
                    "type": item["object"],
                    "title": title,
                    "url": item.get("url", ""),
                    "last_edited": item.get("last_edited_time", ""),
                })

            logger.info("notion_search", query=query, results=len(results))
            return _truncate(json.dumps({"results": results, "count": len(results)}))

    async def _get_page(self, kwargs: dict, headers: dict) -> str:
        page_id = kwargs.get("page_id", "")
        if not page_id:
            return _truncate(json.dumps({"error": "'page_id' is required"}))

        async with httpx.AsyncClient(timeout=15) as client:
            # Get page properties
            resp = await client.get(
                f"{self.API_BASE}/pages/{page_id}",
                headers=headers,
            )

            if resp.status_code != 200:
                return _truncate(json.dumps({
                    "error": f"Failed to get page (status {resp.status_code})",
                    "details": resp.text[:500],
                }))

            page_data = resp.json()

            # Get page content (blocks)
            blocks_resp = await client.get(
                f"{self.API_BASE}/blocks/{page_id}/children",
                headers=headers,
                params={"page_size": 100},
            )

            blocks = []
            if blocks_resp.status_code == 200:
                blocks_data = blocks_resp.json()
                for block in blocks_data.get("results", []):
                    block_type = block.get("type", "")
                    block_content = block.get(block_type, {})

                    text = ""
                    if "rich_text" in block_content:
                        text = "".join(
                            t.get("plain_text", "")
                            for t in block_content["rich_text"]
                        )

                    blocks.append({
                        "id": block["id"],
                        "type": block_type,
                        "text": text,
                    })

            # Extract properties
            properties = {}
            for name, prop in page_data.get("properties", {}).items():
                properties[name] = self._extract_property_value(prop)

            result = {
                "id": page_data["id"],
                "url": page_data.get("url", ""),
                "created_time": page_data.get("created_time", ""),
                "last_edited_time": page_data.get("last_edited_time", ""),
                "properties": properties,
                "content_blocks": blocks,
            }

            logger.info("notion_page_retrieved", page_id=page_id)
            return _truncate(json.dumps(result))

    async def _create_page(self, kwargs: dict, headers: dict) -> str:
        parent_id = kwargs.get("parent_id", "")
        title = kwargs.get("title", "")

        if not parent_id:
            return _truncate(json.dumps({"error": "'parent_id' is required"}))
        if not title:
            return _truncate(json.dumps({"error": "'title' is required"}))

        # Determine parent type
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
                headers=headers,
                json=payload,
            )

            if resp.status_code in (200, 201):
                data = resp.json()
                logger.info("notion_page_created", id=data["id"])
                return _truncate(json.dumps({
                    "success": True,
                    "id": data["id"],
                    "url": data.get("url", ""),
                    "created_time": data.get("created_time", ""),
                }))
            else:
                return _truncate(json.dumps({
                    "error": f"Failed to create page (status {resp.status_code})",
                    "details": resp.text[:500],
                }))

    async def _update_page(self, kwargs: dict, headers: dict) -> str:
        page_id = kwargs.get("page_id", "")
        properties = kwargs.get("properties", {})

        if not page_id:
            return _truncate(json.dumps({"error": "'page_id' is required"}))
        if not properties:
            return _truncate(json.dumps({"error": "'properties' object is required"}))

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.patch(
                f"{self.API_BASE}/pages/{page_id}",
                headers=headers,
                json={"properties": properties},
            )

            if resp.status_code == 200:
                data = resp.json()
                logger.info("notion_page_updated", page_id=page_id)
                return _truncate(json.dumps({
                    "success": True,
                    "id": data["id"],
                    "last_edited_time": data.get("last_edited_time", ""),
                }))
            else:
                return _truncate(json.dumps({
                    "error": f"Failed to update page (status {resp.status_code})",
                    "details": resp.text[:500],
                }))

    async def _get_database(self, kwargs: dict, headers: dict) -> str:
        database_id = kwargs.get("database_id", "")
        if not database_id:
            return _truncate(json.dumps({"error": "'database_id' is required"}))

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.API_BASE}/databases/{database_id}",
                headers=headers,
            )

            if resp.status_code != 200:
                return _truncate(json.dumps({
                    "error": f"Failed to get database (status {resp.status_code})",
                    "details": resp.text[:500],
                }))

            data = resp.json()
            title_parts = data.get("title", [])
            title = "".join(t.get("plain_text", "") for t in title_parts)

            # Extract property schema
            property_schema = {}
            for name, prop in data.get("properties", {}).items():
                schema_entry: dict[str, Any] = {"type": prop.get("type", "")}
                if prop.get("type") == "select":
                    schema_entry["options"] = [
                        o.get("name", "") for o in prop.get("select", {}).get("options", [])
                    ]
                elif prop.get("type") == "multi_select":
                    schema_entry["options"] = [
                        o.get("name", "") for o in prop.get("multi_select", {}).get("options", [])
                    ]
                elif prop.get("type") == "status":
                    schema_entry["options"] = [
                        o.get("name", "") for o in prop.get("status", {}).get("options", [])
                    ]
                property_schema[name] = schema_entry

            logger.info("notion_database_retrieved", database_id=database_id)
            return _truncate(json.dumps({
                "id": data["id"],
                "title": title,
                "url": data.get("url", ""),
                "properties": property_schema,
                "created_time": data.get("created_time", ""),
                "last_edited_time": data.get("last_edited_time", ""),
            }))

    async def _query_database(self, kwargs: dict, headers: dict) -> str:
        database_id = kwargs.get("database_id", "")
        if not database_id:
            return _truncate(json.dumps({"error": "'database_id' is required"}))

        page_size = min(kwargs.get("page_size", 20), 100)
        payload: dict[str, Any] = {"page_size": page_size}

        if kwargs.get("filter"):
            payload["filter"] = kwargs["filter"]
        if kwargs.get("sort"):
            payload["sorts"] = kwargs["sort"]

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.API_BASE}/databases/{database_id}/query",
                headers=headers,
                json=payload,
            )

            if resp.status_code != 200:
                return _truncate(json.dumps({
                    "error": f"Failed to query database (status {resp.status_code})",
                    "details": resp.text[:500],
                }))

            data = resp.json()
            entries = []
            for page in data.get("results", []):
                entry: dict[str, Any] = {
                    "id": page["id"],
                    "url": page.get("url", ""),
                }
                for prop_name, prop_val in page.get("properties", {}).items():
                    entry[prop_name] = self._extract_property_value(prop_val)
                entries.append(entry)

            logger.info("notion_database_queried", database_id=database_id, results=len(entries))
            return _truncate(json.dumps({
                "entries": entries,
                "count": len(entries),
                "has_more": data.get("has_more", False),
            }))
