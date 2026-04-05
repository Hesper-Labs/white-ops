"""Notification tool - send push notifications, email alerts, and webhook alerts."""

import json
import os
from typing import Any

import httpx

from agent.tools.base import BaseTool


class NotificationTool(BaseTool):
    name = "notification"
    description = (
        "Send notifications via multiple channels: push notifications, "
        "email alerts (via internal mail server), and webhook alerts."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["send_push", "send_email_alert", "send_webhook_alert"],
                "description": "The notification action to perform",
            },
            "title": {
                "type": "string",
                "description": "Notification title",
            },
            "message": {
                "type": "string",
                "description": "Notification message body",
            },
            "webhook_url": {
                "type": "string",
                "description": "Webhook URL for send_webhook_alert",
            },
            "to_email": {
                "type": "string",
                "description": "Recipient email for send_email_alert",
            },
            "priority": {
                "type": "string",
                "enum": ["low", "normal", "high", "critical"],
                "description": "Notification priority (default: normal)",
            },
            "payload": {
                "type": "object",
                "description": "Additional payload data for webhook alerts",
            },
            "push_token": {
                "type": "string",
                "description": "Device push token for send_push",
            },
            "push_service": {
                "type": "string",
                "enum": ["ntfy", "pushover", "gotify"],
                "description": "Push notification service (default: ntfy)",
            },
        },
        "required": ["action", "message"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]
        try:
            if action == "send_push":
                return await self._send_push(kwargs)
            elif action == "send_email_alert":
                return await self._send_email_alert(kwargs)
            elif action == "send_webhook_alert":
                return await self._send_webhook_alert(kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except httpx.HTTPError as e:
            return json.dumps({"error": f"Request failed: {e}"})
        except Exception as e:
            return json.dumps({"error": f"Notification failed: {e}"})

    async def _send_push(self, kwargs: dict) -> str:
        message = kwargs.get("message", "")
        title = kwargs.get("title", "White-Ops Notification")
        priority = kwargs.get("priority", "normal")
        service = kwargs.get("push_service", "ntfy")

        if service == "ntfy":
            topic = os.environ.get("NTFY_TOPIC", "whiteops")
            ntfy_url = os.environ.get("NTFY_URL", "https://ntfy.sh")

            priority_map = {"low": "2", "normal": "3", "high": "4", "critical": "5"}

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{ntfy_url}/{topic}",
                    headers={
                        "Title": title,
                        "Priority": priority_map.get(priority, "3"),
                        "Tags": "white_check_mark",
                    },
                    content=message.encode("utf-8"),
                )
                if resp.status_code == 200:
                    return json.dumps({"success": True, "service": "ntfy", "topic": topic})
                return json.dumps({"error": f"ntfy returned status {resp.status_code}"})

        elif service == "pushover":
            token = os.environ.get("PUSHOVER_APP_TOKEN", "")
            user = os.environ.get("PUSHOVER_USER_KEY", "")
            if not token or not user:
                return json.dumps({"error": "PUSHOVER_APP_TOKEN and PUSHOVER_USER_KEY are required"})

            priority_map = {"low": "-1", "normal": "0", "high": "1", "critical": "2"}

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    "https://api.pushover.net/1/messages.json",
                    data={
                        "token": token,
                        "user": user,
                        "title": title,
                        "message": message,
                        "priority": priority_map.get(priority, "0"),
                    },
                )
                data = resp.json()
                if data.get("status") == 1:
                    return json.dumps({"success": True, "service": "pushover"})
                return json.dumps({"error": data.get("errors", ["Unknown error"])})

        elif service == "gotify":
            gotify_url = os.environ.get("GOTIFY_URL", "")
            gotify_token = os.environ.get("GOTIFY_APP_TOKEN", "")
            if not gotify_url or not gotify_token:
                return json.dumps({"error": "GOTIFY_URL and GOTIFY_APP_TOKEN are required"})

            priority_map = {"low": 2, "normal": 5, "high": 7, "critical": 10}

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{gotify_url.rstrip('/')}/message",
                    headers={"X-Gotify-Key": gotify_token},
                    json={
                        "title": title,
                        "message": message,
                        "priority": priority_map.get(priority, 5),
                    },
                )
                if resp.status_code == 200:
                    return json.dumps({"success": True, "service": "gotify"})
                return json.dumps({"error": f"Gotify returned status {resp.status_code}"})

        return json.dumps({"error": f"Unsupported push service: {service}"})

    async def _send_email_alert(self, kwargs: dict) -> str:
        from agent.config import settings

        to_email = kwargs.get("to_email")
        if not to_email:
            return json.dumps({"error": "to_email is required"})

        title = kwargs.get("title", "White-Ops Alert")
        message = kwargs.get("message", "")
        priority = kwargs.get("priority", "normal")

        import aiosmtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["Subject"] = f"[{priority.upper()}] {title}"
        msg["From"] = f"alerts@{settings.mail_domain}"
        msg["To"] = to_email
        msg.set_content(message)

        try:
            await aiosmtplib.send(
                msg,
                hostname=settings.mail_server_host,
                port=settings.mail_server_port,
                use_tls=False,
            )
            return json.dumps({
                "success": True,
                "to": to_email,
                "subject": msg["Subject"],
            })
        except Exception as e:
            return json.dumps({"error": f"Email sending failed: {e}"})

    async def _send_webhook_alert(self, kwargs: dict) -> str:
        webhook_url = kwargs.get("webhook_url")
        if not webhook_url:
            webhook_url = os.environ.get("ALERT_WEBHOOK_URL", "")
        if not webhook_url:
            return json.dumps({"error": "webhook_url is required (param or ALERT_WEBHOOK_URL env)"})

        title = kwargs.get("title", "White-Ops Alert")
        message = kwargs.get("message", "")
        priority = kwargs.get("priority", "normal")
        extra_payload = kwargs.get("payload", {})

        payload = {
            "title": title,
            "message": message,
            "priority": priority,
            "source": "whiteops",
            **extra_payload,
        }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            return json.dumps({
                "success": resp.status_code < 400,
                "status_code": resp.status_code,
                "webhook_url": webhook_url,
            })
