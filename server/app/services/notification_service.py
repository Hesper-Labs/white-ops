"""Notification service - multi-channel notifications with rules engine and user preferences."""

import hashlib
import hmac
import json
import uuid
from datetime import UTC, datetime

import httpx
import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationRule, UserNotificationPreference

logger = structlog.get_logger()

# Severity ordering for filtering
SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2, "critical": 3}


class NotificationService:
    """Multi-channel notification service with rules, user preferences, and delivery."""

    def __init__(self):
        self._http_client: httpx.AsyncClient | None = None

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    # ------------------------------------------------------------------
    # Core send
    # ------------------------------------------------------------------

    async def send(
        self,
        db: AsyncSession,
        channel: str,
        subject: str,
        body: str,
        severity: str = "info",
        user_id: uuid.UUID | None = None,
        metadata: dict | None = None,
    ) -> Notification:
        """Create a notification record and attempt delivery on the specified channel."""
        log = logger.bind(channel=channel, severity=severity)

        notification = Notification(
            channel=channel,
            subject=subject,
            body=body,
            severity=severity,
            user_id=user_id,
            metadata_=metadata or {},
        )
        db.add(notification)
        await db.flush()

        # Attempt channel-specific delivery
        try:
            config = metadata or {}
            if channel == "email":
                await self.send_email(
                    to=config.get("to", ""),
                    subject=subject,
                    body=body,
                )
            elif channel == "slack":
                await self.send_slack(
                    webhook_url=config.get("webhook_url", ""),
                    message=f"*{subject}*\n{body}",
                )
            elif channel == "webhook":
                await self.send_webhook(
                    url=config.get("url", ""),
                    payload={"subject": subject, "body": body, "severity": severity},
                    secret=config.get("secret"),
                )
            elif channel == "telegram":
                await self.send_telegram(
                    chat_id=config.get("chat_id", ""),
                    message=f"*{subject}*\n{body}",
                )
            # in_app channel needs no external delivery
        except Exception as exc:
            log.error("notification_delivery_failed", error=str(exc))

        log.info("notification_sent", notification_id=str(notification.id))
        return notification

    # ------------------------------------------------------------------
    # Channel implementations
    # ------------------------------------------------------------------

    async def send_email(self, to: str, subject: str, body: str) -> None:
        """Send an email via aiosmtplib."""
        if not to:
            logger.warning("notification_email_no_recipient")
            return

        try:
            from email.message import EmailMessage

            import aiosmtplib

            from app.config import settings

            msg = EmailMessage()
            msg["From"] = f"noreply@{settings.mail_domain}"
            msg["To"] = to
            msg["Subject"] = subject
            msg.set_content(body)

            await aiosmtplib.send(
                msg,
                hostname=settings.mail_server_host,
                port=settings.mail_server_port,
            )
            logger.info("notification_email_sent", to=to)
        except ImportError:
            logger.warning("notification_email_aiosmtplib_not_installed")
        except Exception as exc:
            logger.error("notification_email_failed", to=to, error=str(exc))
            raise

    async def send_slack(self, webhook_url: str, message: str) -> None:
        """Send a message to Slack via incoming webhook."""
        if not webhook_url:
            logger.warning("notification_slack_no_webhook")
            return

        client = await self._get_http_client()
        response = await client.post(
            webhook_url,
            json={"text": message},
            headers={"Content-Type": "application/json"},
        )
        if response.status_code != 200:
            logger.error("notification_slack_failed", status=response.status_code, body=response.text)
            raise RuntimeError(f"Slack webhook returned {response.status_code}")
        logger.info("notification_slack_sent")

    async def send_webhook(
        self,
        url: str,
        payload: dict,
        secret: str | None = None,
    ) -> None:
        """Send a webhook with optional HMAC-SHA256 signing."""
        if not url:
            logger.warning("notification_webhook_no_url")
            return

        body = json.dumps(payload, default=str)
        headers: dict[str, str] = {"Content-Type": "application/json"}

        if secret:
            signature = hmac.new(
                secret.encode(),
                body.encode(),
                hashlib.sha256,
            ).hexdigest()
            headers["X-Signature-256"] = f"sha256={signature}"

        client = await self._get_http_client()
        response = await client.post(url, content=body, headers=headers)
        if response.status_code >= 400:
            logger.error("notification_webhook_failed", status=response.status_code)
            raise RuntimeError(f"Webhook returned {response.status_code}")
        logger.info("notification_webhook_sent", url=url)

    async def send_telegram(self, chat_id: str, message: str) -> None:
        """Send a message via Telegram Bot API."""
        import os

        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            logger.warning("notification_telegram_no_token")
            return
        if not chat_id:
            logger.warning("notification_telegram_no_chat_id")
            return

        client = await self._get_http_client()
        response = await client.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
            },
        )
        if response.status_code != 200:
            logger.error("notification_telegram_failed", status=response.status_code, body=response.text)
            raise RuntimeError(f"Telegram API returned {response.status_code}")
        logger.info("notification_telegram_sent", chat_id=chat_id)

    # ------------------------------------------------------------------
    # Rules engine
    # ------------------------------------------------------------------

    async def process_rules(
        self,
        event_type: str,
        event_data: dict,
        db: AsyncSession,
    ) -> list[Notification]:
        """Evaluate notification rules for a given event and fire matching notifications."""
        log = logger.bind(event_type=event_type)

        result = await db.execute(
            select(NotificationRule).where(
                and_(
                    NotificationRule.event_type == event_type,
                    NotificationRule.is_active.is_(True),
                    NotificationRule.is_deleted.is_(False),
                )
            )
        )
        rules = list(result.scalars().all())
        sent: list[Notification] = []

        for rule in rules:
            # Check conditions (simple key-value matching)
            conditions = rule.conditions or {}
            match = True
            for key, expected in conditions.items():
                actual = event_data.get(key)
                if actual != expected:
                    match = False
                    break

            if not match:
                continue

            # Build notification from template or defaults
            subject = (rule.template or "").format(**event_data) if rule.template else f"Event: {event_type}"
            body = json.dumps(event_data, default=str)
            config = rule.config or {}

            notification = await self.send(
                db=db,
                channel=rule.channel,
                subject=subject,
                body=body,
                severity=config.get("severity", "info"),
                user_id=uuid.UUID(config["user_id"]) if config.get("user_id") else None,
                metadata=config,
            )
            sent.append(notification)

        log.info("notification_rules_processed", matched=len(sent), total_rules=len(rules))
        return sent

    # ------------------------------------------------------------------
    # User preferences
    # ------------------------------------------------------------------

    async def get_user_preferences(self, user_id: uuid.UUID, db: AsyncSession) -> dict:
        """Get notification preferences for a user."""
        result = await db.execute(
            select(UserNotificationPreference).where(
                UserNotificationPreference.user_id == user_id
            )
        )
        pref = result.scalar_one_or_none()
        if not pref:
            return {
                "email_enabled": True,
                "slack_enabled": True,
                "telegram_enabled": False,
                "webhook_enabled": False,
                "min_severity": "info",
                "quiet_hours_start": None,
                "quiet_hours_end": None,
            }

        return {
            "email_enabled": pref.email_enabled,
            "slack_enabled": pref.slack_enabled,
            "telegram_enabled": pref.telegram_enabled,
            "webhook_enabled": pref.webhook_enabled,
            "min_severity": pref.min_severity,
            "quiet_hours_start": pref.quiet_hours_start,
            "quiet_hours_end": pref.quiet_hours_end,
            "config": pref.config,
        }

    # ------------------------------------------------------------------
    # Read / unread management
    # ------------------------------------------------------------------

    async def mark_read(self, notification_id: uuid.UUID, db: AsyncSession) -> bool:
        """Mark a notification as read."""
        result = await db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.is_deleted.is_(False),
            )
        )
        notification = result.scalar_one_or_none()
        if not notification:
            return False

        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        await db.flush()
        return True

    async def get_unread_count(self, user_id: uuid.UUID, db: AsyncSession) -> int:
        """Get the number of unread notifications for a user."""
        result = await db.execute(
            select(func.count(Notification.id)).where(
                and_(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                    Notification.is_deleted.is_(False),
                )
            )
        )
        return result.scalar() or 0


notification_service = NotificationService()
