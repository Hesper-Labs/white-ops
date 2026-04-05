"""API caller tool - make HTTP requests to external APIs."""

import json
from typing import Any

import httpx

from agent.tools.base import BaseTool


class APICallerTool(BaseTool):
    name = "api_caller"
    description = (
        "Make HTTP requests to external REST APIs. "
        "Supports GET, POST, PUT, PATCH, DELETE with headers, body, and auth."
    )
    parameters = {
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
            },
            "url": {"type": "string"},
            "headers": {"type": "object"},
            "body": {"type": "object", "description": "JSON body for POST/PUT/PATCH"},
            "params": {"type": "object", "description": "Query parameters"},
            "timeout": {"type": "integer", "description": "Timeout in seconds"},
        },
        "required": ["method", "url"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        method = kwargs["method"]
        url = kwargs["url"]
        headers = kwargs.get("headers", {})
        body = kwargs.get("body")
        params = kwargs.get("params")
        timeout = kwargs.get("timeout", 30)

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=body if body else None,
                params=params,
            )

            # Try to parse as JSON
            try:
                data = response.json()
            except Exception:
                data = response.text[:5000]

            return json.dumps({
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": data,
            }, ensure_ascii=False)
