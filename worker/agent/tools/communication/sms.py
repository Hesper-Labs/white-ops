"""SMS tool - send SMS messages via Twilio (placeholder, needs API keys)."""

import json
import os
from typing import Any

from agent.tools.base import BaseTool


class SMSTool(BaseTool):
    name = "sms"
    description = (
        "Send SMS messages using Twilio. "
        "NOTE: Requires Twilio Account SID, Auth Token, and a Twilio phone number."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["send_sms"],
                "description": "SMS action to perform",
            },
            "to": {
                "type": "string",
                "description": "Recipient phone number in E.164 format (e.g., +15551234567)",
            },
            "body": {
                "type": "string",
                "description": "SMS message body (max 1600 characters)",
            },
            "from_number": {
                "type": "string",
                "description": "Twilio phone number to send from (overrides default)",
            },
        },
        "required": ["action", "to", "body"],
    }

    def _get_config(self) -> tuple[str, str, str]:
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        from_number = os.environ.get("TWILIO_PHONE_NUMBER", "")
        if not all([account_sid, auth_token, from_number]):
            raise ValueError(
                "TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and TWILIO_PHONE_NUMBER "
                "environment variables are required for SMS"
            )
        return account_sid, auth_token, from_number

    async def execute(self, **kwargs: Any) -> Any:
        if kwargs.get("action") != "send_sms":
            return json.dumps({"error": "Only 'send_sms' action is supported"})

        to = kwargs.get("to", "")
        body = kwargs.get("body", "")

        if not to or not body:
            return json.dumps({"error": "to and body are required"})

        # Validate phone number format
        if not to.startswith("+"):
            return json.dumps({"error": "Phone number must be in E.164 format (e.g., +15551234567)"})

        # Truncate body if too long
        if len(body) > 1600:
            body = body[:1600]

        try:
            account_sid, auth_token, default_from = self._get_config()
        except ValueError as e:
            return json.dumps({"error": str(e)})

        from_number = kwargs.get("from_number", default_from)

        try:
            import httpx

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json",
                    auth=(account_sid, auth_token),
                    data={
                        "To": to,
                        "From": from_number,
                        "Body": body,
                    },
                )

                if resp.status_code == 201:
                    data = resp.json()
                    return json.dumps({
                        "success": True,
                        "sid": data.get("sid", ""),
                        "status": data.get("status", ""),
                        "to": data.get("to", to),
                        "from": data.get("from", from_number),
                    })
                else:
                    try:
                        err = resp.json()
                        return json.dumps({
                            "error": err.get("message", f"Status {resp.status_code}"),
                            "code": err.get("code"),
                        })
                    except Exception:
                        return json.dumps({"error": f"Twilio returned status {resp.status_code}"})
        except ImportError:
            return json.dumps({"error": "httpx is required for SMS sending"})
        except Exception as e:
            return json.dumps({"error": f"SMS sending failed: {e}"})
