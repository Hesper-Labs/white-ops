"""Currency conversion tool - convert currencies with caching and historical rates."""

import json
import time
from typing import Any

import httpx
import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
CACHE_TTL = 3600  # 1 hour in seconds


def _truncate(result: str) -> str:
    if len(result) > MAX_OUTPUT_BYTES:
        return result[:MAX_OUTPUT_BYTES] + "\n... [output truncated at 50KB]"
    return result


class CurrencyTool(BaseTool):
    name = "currency"
    description = (
        "Convert between currencies using live exchange rates. "
        "Supports conversion, listing rates, and historical rate lookups. "
        "Rates are cached for 1 hour. Uses exchangerate-api.com and frankfurter.app (free)."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["convert", "rates", "historical"],
                "description": "Currency action.",
            },
            "amount": {
                "type": "number",
                "description": "Amount to convert (for convert).",
            },
            "from_currency": {
                "type": "string",
                "description": "Source currency code (e.g., USD, EUR).",
            },
            "to_currency": {
                "type": "string",
                "description": "Target currency code (for convert).",
            },
            "base_currency": {
                "type": "string",
                "description": "Base currency for rates listing (default: USD).",
            },
            "date": {
                "type": "string",
                "description": "Historical date (YYYY-MM-DD) for historical rates.",
            },
            "base": {
                "type": "string",
                "description": "Base currency for historical rates.",
            },
            "symbols": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of currency codes for historical lookup.",
            },
        },
        "required": ["action"],
    }

    # Class-level cache
    _rates_cache: dict[str, tuple[float, dict]] = {}

    def _get_cached_rates(self, base: str) -> dict | None:
        """Get cached rates if still valid."""
        if base in self._rates_cache:
            cached_time, rates = self._rates_cache[base]
            if time.time() - cached_time < CACHE_TTL:
                logger.debug("currency_cache_hit", base=base)
                return rates
        return None

    def _set_cached_rates(self, base: str, rates: dict) -> None:
        """Cache rates with timestamp."""
        self._rates_cache[base] = (time.time(), rates)

    async def _fetch_rates(self, base: str) -> dict:
        """Fetch current rates, using cache if available."""
        cached = self._get_cached_rates(base)
        if cached is not None:
            return cached

        # Try exchangerate-api.com first
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"https://open.er-api.com/v6/latest/{base}")
                resp.raise_for_status()
                data = resp.json()

            if data.get("result") == "success":
                result = {
                    "rates": data.get("rates", {}),
                    "last_update": data.get("time_last_update_utc", ""),
                    "source": "exchangerate-api",
                }
                self._set_cached_rates(base, result)
                return result
        except Exception as e:
            logger.warning("exchangerate_api_failed", error=str(e))

        # Fallback to frankfurter.app
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"https://api.frankfurter.app/latest?from={base}")
                resp.raise_for_status()
                data = resp.json()

            rates = data.get("rates", {})
            rates[base] = 1.0  # Add base currency
            result = {
                "rates": rates,
                "last_update": data.get("date", ""),
                "source": "frankfurter",
            }
            self._set_cached_rates(base, result)
            return result
        except Exception as e:
            logger.error("frankfurter_api_failed", error=str(e))
            raise ValueError(f"Failed to fetch exchange rates from all sources: {e}")

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "")
        logger.info("currency_execute", action=action)

        try:
            if action == "convert":
                return await self._convert(kwargs)
            elif action == "rates":
                return await self._rates(kwargs)
            elif action == "historical":
                return await self._historical(kwargs)
            else:
                return _truncate(json.dumps({"error": f"Unknown action: {action}"}))
        except Exception as e:
            logger.error("currency_failed", action=action, error=str(e))
            return _truncate(json.dumps({"error": f"Currency operation failed: {e}"}))

    async def _convert(self, kwargs: dict) -> str:
        amount = kwargs.get("amount", 1.0)
        from_cur = kwargs.get("from_currency", "USD").upper()
        to_cur = kwargs.get("to_currency", "").upper()

        if not to_cur:
            return _truncate(json.dumps({"error": "'to_currency' is required"}))
        if amount <= 0:
            return _truncate(json.dumps({"error": "'amount' must be positive"}))

        data = await self._fetch_rates(from_cur)
        rates = data["rates"]

        if to_cur not in rates:
            return _truncate(json.dumps({"error": f"Currency '{to_cur}' not found"}))

        rate = rates[to_cur]
        converted = round(amount * rate, 4)

        logger.info("currency_converted", from_=from_cur, to=to_cur, amount=amount, result=converted)
        return _truncate(json.dumps({
            "from": from_cur,
            "to": to_cur,
            "amount": amount,
            "rate": rate,
            "result": converted,
            "last_update": data.get("last_update", ""),
            "source": data.get("source", ""),
        }))

    async def _rates(self, kwargs: dict) -> str:
        base = kwargs.get("base_currency", "USD").upper()

        data = await self._fetch_rates(base)

        logger.info("currency_rates", base=base, count=len(data["rates"]))
        return _truncate(json.dumps({
            "base": base,
            "rates": data["rates"],
            "currencies_count": len(data["rates"]),
            "last_update": data.get("last_update", ""),
            "source": data.get("source", ""),
        }))

    async def _historical(self, kwargs: dict) -> str:
        date = kwargs.get("date", "")
        base = kwargs.get("base", "USD").upper()
        symbols = kwargs.get("symbols", [])

        if not date:
            return _truncate(json.dumps({"error": "'date' is required (YYYY-MM-DD)"}))

        # Use frankfurter.app for historical data (free, no key needed)
        params = f"from={base}"
        if symbols:
            params += f"&to={','.join(s.upper() for s in symbols)}"

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(f"https://api.frankfurter.app/{date}?{params}")
                resp.raise_for_status()
                data = resp.json()

            rates = data.get("rates", {})

            logger.info("currency_historical", date=date, base=base, count=len(rates))
            return _truncate(json.dumps({
                "date": data.get("date", date),
                "base": base,
                "rates": rates,
                "source": "frankfurter",
            }))
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return _truncate(json.dumps({"error": f"No historical data available for {date}"}))
            raise
