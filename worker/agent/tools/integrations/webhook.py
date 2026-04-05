"""Webhook tool - send and receive webhooks for third-party integrations."""

import json
from typing import Any

import httpx

from agent.tools.base import BaseTool


class WebhookTool(BaseTool):
    name = "webhook"
    description = (
        "Send webhooks to external services (Slack, Discord, Zapier, n8n, etc.). "
        "Trigger automations and send notifications."
    )
    parameters = {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "Webhook URL"},
            "payload": {"type": "object", "description": "JSON payload to send"},
            "method": {"type": "string", "enum": ["POST", "PUT"], "description": "HTTP method"},
            "headers": {"type": "object", "description": "Custom headers"},
        },
        "required": ["url", "payload"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        url = kwargs["url"]
        payload = kwargs["payload"]
        method = kwargs.get("method", "POST")
        headers = kwargs.get("headers", {"Content-Type": "application/json"})

        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.request(
                method=method,
                url=url,
                json=payload,
                headers=headers,
            )

            return json.dumps({
                "status_code": response.status_code,
                "success": 200 <= response.status_code < 300,
                "response": response.text[:1000],
            })
