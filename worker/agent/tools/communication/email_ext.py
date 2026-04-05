"""External email tool - send and receive emails via SMTP/IMAP."""

import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from typing import Any

from agent.tools.base import BaseTool


class ExternalEmailTool(BaseTool):
    name = "external_email"
    description = (
        "Send and receive external emails via SMTP/IMAP. "
        "Supports: send with attachments, check inbox, read emails, search."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["send", "check_inbox", "read", "search"],
            },
            "to": {"type": "array", "items": {"type": "string"}, "description": "Recipient emails"},
            "cc": {"type": "array", "items": {"type": "string"}},
            "subject": {"type": "string"},
            "body": {"type": "string"},
            "html": {"type": "boolean", "description": "Send as HTML email"},
            "attachments": {"type": "array", "items": {"type": "string"}, "description": "File paths"},
            "folder": {"type": "string", "description": "IMAP folder (default: INBOX)"},
            "query": {"type": "string", "description": "Search query for IMAP"},
            "limit": {"type": "integer"},
        },
        "required": ["action"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]

        if action == "send":
            return await self._send(kwargs)
        elif action in ("check_inbox", "read", "search"):
            return await self._read(action, kwargs)
        return f"Unknown action: {action}"

    async def _send(self, kwargs: dict) -> str:
        import aiosmtplib
        from agent.config import settings

        smtp_host = settings.mail_server_host  # Will use external SMTP when configured
        smtp_port = settings.mail_server_port

        msg = MIMEMultipart()
        msg["Subject"] = kwargs.get("subject", "")
        msg["To"] = ", ".join(kwargs.get("to", []))
        if kwargs.get("cc"):
            msg["Cc"] = ", ".join(kwargs["cc"])

        body = kwargs.get("body", "")
        subtype = "html" if kwargs.get("html") else "plain"
        msg.attach(MIMEText(body, subtype))

        # Attachments
        for filepath in kwargs.get("attachments", []):
            if Path(filepath).exists():
                with open(filepath, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={Path(filepath).name}")
                    msg.attach(part)

        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
        )

        return f"Email sent to {msg['To']}"

    async def _read(self, action: str, kwargs: dict) -> str:
        # Placeholder - IMAP reading requires credentials
        return json.dumps({
            "status": "imap_not_configured",
            "message": "Configure IMAP settings in the admin panel to read external emails.",
        })
