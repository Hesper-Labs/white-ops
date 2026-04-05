"""Currency tool - convert currencies using live exchange rates."""

from typing import Any

import httpx

from agent.tools.base import BaseTool

API_BASE = "https://open.er-api.com/v6"


class CurrencyTool(BaseTool):
    name = "currency"
    description = (
        "Convert between currencies and list exchange rates using live data. "
        "Supports all major world currencies."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["convert", "list_rates"],
                "description": "Action to perform.",
            },
            "from_currency": {
                "type": "string",
                "description": "Source currency code (e.g., USD, EUR, TRY).",
            },
            "to_currency": {
                "type": "string",
                "description": "Target currency code (for convert).",
            },
            "amount": {
                "type": "number",
                "description": "Amount to convert (for convert).",
            },
        },
        "required": ["action"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs["action"]

        if action == "convert":
            from_cur = kwargs.get("from_currency", "USD").upper()
            to_cur = kwargs.get("to_currency", "TRY").upper()
            amount = kwargs.get("amount", 1.0)

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{API_BASE}/latest/{from_cur}")
                resp.raise_for_status()
                data = resp.json()

            if data.get("result") != "success":
                return {"error": f"API error: {data.get('error-type', 'unknown')}"}

            rates = data.get("rates", {})
            if to_cur not in rates:
                return {"error": f"Currency {to_cur} not found in rates."}

            rate = rates[to_cur]
            converted = round(amount * rate, 4)
            return {
                "from": from_cur,
                "to": to_cur,
                "amount": amount,
                "rate": rate,
                "result": converted,
                "last_update": data.get("time_last_update_utc", ""),
            }

        elif action == "list_rates":
            base = kwargs.get("from_currency", "USD").upper()

            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"{API_BASE}/latest/{base}")
                resp.raise_for_status()
                data = resp.json()

            if data.get("result") != "success":
                return {"error": f"API error: {data.get('error-type', 'unknown')}"}

            return {
                "base": base,
                "rates": data.get("rates", {}),
                "last_update": data.get("time_last_update_utc", ""),
            }

        return {"error": f"Unknown action: {action}"}
