"""White-Ops Internal Mail Server.

A lightweight SMTP server for agent-to-agent communication.
Messages are stored in Redis and accessible via the REST API.
"""

import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from email import message_from_bytes

import redis
import structlog
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import Envelope, Session, SMTP

logger = structlog.get_logger()

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_PASSWORD = os.environ.get("REDIS_PASSWORD", "changeme")
MAIL_DOMAIN = os.environ.get("MAIL_DOMAIN", "whiteops.local")


class WhiteOpsMailHandler:
    def __init__(self) -> None:
        self.redis = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            decode_responses=True,
        )
        logger.info("mail_handler_initialized", domain=MAIL_DOMAIN)

    async def handle_RCPT(
        self,
        server: SMTP,
        session: Session,
        envelope: Envelope,
        address: str,
        rcpt_options: list,
    ) -> str:
        if not address.endswith(f"@{MAIL_DOMAIN}"):
            return f"550 Recipient must be @{MAIL_DOMAIN}"
        envelope.rcpt_tos.append(address)
        return "250 OK"

    async def handle_DATA(
        self,
        server: SMTP,
        session: Session,
        envelope: Envelope,
    ) -> str:
        msg = message_from_bytes(envelope.content)

        mail_data = {
            "id": str(uuid.uuid4()),
            "from": envelope.mail_from,
            "to": envelope.rcpt_tos,
            "subject": msg.get("subject", "(no subject)"),
            "body": self._extract_body(msg),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "read": False,
        }

        # Store in Redis for each recipient
        for recipient in envelope.rcpt_tos:
            mailbox_key = f"mailbox:{recipient}"
            self.redis.lpush(mailbox_key, json.dumps(mail_data))
            # Keep only last 1000 messages per mailbox
            self.redis.ltrim(mailbox_key, 0, 999)

        # Publish event for real-time notifications
        self.redis.publish(
            "mail:new",
            json.dumps({
                "id": mail_data["id"],
                "from": mail_data["from"],
                "to": mail_data["to"],
                "subject": mail_data["subject"],
            }),
        )

        logger.info(
            "mail_received",
            from_addr=envelope.mail_from,
            to=envelope.rcpt_tos,
            subject=mail_data["subject"],
        )

        return "250 Message accepted"

    def _extract_body(self, msg) -> str:
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode("utf-8", errors="replace")
            return ""
        return msg.get_payload(decode=True).decode("utf-8", errors="replace")


async def main() -> None:
    handler = WhiteOpsMailHandler()
    controller = Controller(
        handler,
        hostname="0.0.0.0",
        port=8025,
    )

    logger.info("mail_server_starting", port=8025, domain=MAIL_DOMAIN)
    controller.start()

    try:
        while True:
            await asyncio.sleep(3600)
    except (KeyboardInterrupt, asyncio.CancelledError):
        controller.stop()
        logger.info("mail_server_stopped")


if __name__ == "__main__":
    asyncio.run(main())
