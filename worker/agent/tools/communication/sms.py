"""SMS tool - send SMS messages via Twilio REST API."""

import json
import os
from typing import Any

import httpx
import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024  # 50KB


def _truncate(result: str) -> str:
    if len(result) > MAX_OUTPUT_BYTES:
        return result[:MAX_OUTPUT_BYTES] + "\n... [output truncated at 50KB]"
    return result


class SMSTool(BaseTool):
    name = "sms"
    description = (
        "Send SMS messages via Twilio. Supports sending single messages, "
        "bulk messages to multiple recipients, and checking message delivery status. "
        "Requires TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER env vars."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["send", "send_bulk", "check_status"],
                "description": "SMS action to perform.",
            },
            "to": {
                "type": "string",
                "description": "Recipient phone number in E.164 format (for send).",
            },
            "body": {
                "type": "string",
                "description": "SMS message body (max 1600 characters).",
            },
            "from_number": {
                "type": "string",
                "description": "Twilio phone number to send from (overrides default).",
            },
            "recipients": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of phone numbers in E.164 format (for send_bulk).",
            },
            "message_sid": {
                "type": "string",
                "description": "Twilio message SID to check status of.",
            },
        },
        "required": ["action"],
    }

    def _get_config(self) -> tuple[str, str, str]:
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        from_number = os.environ.get("TWILIO_PHONE_NUMBER", "")
        if not all([account_sid, auth_token, from_number]):
            raise ValueError(
                "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER "
                "environment variables are required"
            )
        return account_sid, auth_token, from_number

    async def _send_single(
        self,
        client: httpx.AsyncClient,
        account_sid: str,
        auth_token: str,
        from_number: str,
        to: str,
        body: str,
    ) -> dict:
        """Send a single SMS message via Twilio API."""
        resp = await client.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
            auth=(account_sid, auth_token),
            data={"To": to, "From": from_number, "Body": body},
        )

        if resp.status_code == 201:
            data = resp.json()
            return {
                "success": True,
                "sid": data.get("sid", ""),
                "status": data.get("status", ""),
                "to": data.get("to", to),
                "from": data.get("from", from_number),
            }
        else:
            try:
                err = resp.json()
                return {
                    "success": False,
                    "error": err.get("message", f"Status {resp.status_code}"),
                    "code": err.get("code"),
                    "to": to,
                }
            except Exception:
                return {
                    "success": False,
                    "error": f"Twilio returned status {resp.status_code}",
                    "to": to,
                }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "")
        logger.info("sms_tool_execute", action=action)

        try:
            account_sid, auth_token, default_from = self._get_config()
        except ValueError as e:
            logger.error("sms_config_error", error=str(e))
            return _truncate(json.dumps({"error": str(e)}))

        from_number = kwargs.get("from_number", default_from)

        if action == "send":
            to = kwargs.get("to", "")
            body = kwargs.get("body", "")

            if not to or not body:
                return _truncate(json.dumps({"error": "'to' and 'body' are required for send"}))

            if not to.startswith("+"):
                return _truncate(json.dumps({"error": "Phone number must be in E.164 format (e.g., +15551234567)"}))

            if len(body) > 1600:
                body = body[:1600]

            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    result = await self._send_single(client, account_sid, auth_token, from_number, to, body)
                    logger.info("sms_sent", to=to, success=result.get("success"))
                    return _truncate(json.dumps(result))
            except Exception as e:
                logger.error("sms_send_failed", to=to, error=str(e))
                return _truncate(json.dumps({"error": f"SMS sending failed: {e}"}))

        elif action == "send_bulk":
            recipients = kwargs.get("recipients", [])
            body = kwargs.get("body", "")

            if not recipients:
                return _truncate(json.dumps({"error": "'recipients' list is required for send_bulk"}))
            if not body:
                return _truncate(json.dumps({"error": "'body' is required for send_bulk"}))

            if len(body) > 1600:
                body = body[:1600]

            invalid = [r for r in recipients if not r.startswith("+")]
            if invalid:
                return _truncate(json.dumps({
                    "error": "All phone numbers must be in E.164 format",
                    "invalid_numbers": invalid[:10],
                }))

            results = []
            succeeded = 0
            failed = 0

            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    for to in recipients:
                        result = await self._send_single(client, account_sid, auth_token, from_number, to, body)
                        results.append(result)
                        if result.get("success"):
                            succeeded += 1
                        else:
                            failed += 1

                logger.info("sms_bulk_sent", total=len(recipients), succeeded=succeeded, failed=failed)
                return _truncate(json.dumps({
                    "total": len(recipients),
                    "succeeded": succeeded,
                    "failed": failed,
                    "results": results,
                }))
            except Exception as e:
                logger.error("sms_bulk_failed", error=str(e))
                return _truncate(json.dumps({"error": f"Bulk SMS failed: {e}"}))

        elif action == "check_status":
            message_sid = kwargs.get("message_sid", "")
            if not message_sid:
                return _truncate(json.dumps({"error": "'message_sid' is required for check_status"}))

            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.get(
                        f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages/{message_sid}.json",
                        auth=(account_sid, auth_token),
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        result = {
                            "sid": data.get("sid", ""),
                            "status": data.get("status", ""),
                            "to": data.get("to", ""),
                            "from": data.get("from", ""),
                            "body": data.get("body", ""),
                            "date_sent": data.get("date_sent", ""),
                            "date_created": data.get("date_created", ""),
                            "error_code": data.get("error_code"),
                            "error_message": data.get("error_message"),
                            "price": data.get("price"),
                            "price_unit": data.get("price_unit"),
                        }
                        logger.info("sms_status_checked", sid=message_sid, status=result["status"])
                        return _truncate(json.dumps(result))
                    else:
                        return _truncate(json.dumps({"error": f"Twilio returned status {resp.status_code}"}))
            except Exception as e:
                logger.error("sms_status_check_failed", sid=message_sid, error=str(e))
                return _truncate(json.dumps({"error": f"Status check failed: {e}"}))

        return _truncate(json.dumps({"error": f"Unknown action: {action}"}))
