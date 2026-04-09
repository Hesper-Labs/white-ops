"""Prometheus query tool - query metrics via Prometheus HTTP API."""

import json
from typing import Any

import httpx
import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_BYTES:
        return text[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
    return text


class PrometheusTool(BaseTool):
    name = "prometheus"
    description = (
        "Query Prometheus metrics using PromQL. Supports instant queries, "
        "range queries, listing alerts, and listing scrape targets."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["query", "query_range", "alerts", "targets"],
                "description": "Prometheus action to perform.",
            },
            "prometheus_url": {
                "type": "string",
                "description": "Base URL of the Prometheus server (e.g. http://prometheus:9090).",
            },
            "promql": {
                "type": "string",
                "description": "PromQL query expression (for query, query_range).",
            },
            "start": {
                "type": "string",
                "description": "Start time for range query (RFC3339 or Unix timestamp).",
            },
            "end": {
                "type": "string",
                "description": "End time for range query (RFC3339 or Unix timestamp).",
            },
            "step": {
                "type": "string",
                "description": "Query step for range query (e.g. '15s', '1m', '5m'). Default: '1m'.",
            },
        },
        "required": ["action", "prometheus_url"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action")
        prometheus_url = kwargs.get("prometheus_url", "").rstrip("/")
        logger.info("prometheus_execute", action=action)

        if not prometheus_url:
            return json.dumps({"error": "prometheus_url is required"})

        try:
            if action == "query":
                return await self._query(prometheus_url, kwargs)
            elif action == "query_range":
                return await self._query_range(prometheus_url, kwargs)
            elif action == "alerts":
                return await self._alerts(prometheus_url)
            elif action == "targets":
                return await self._targets(prometheus_url)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except httpx.TimeoutException:
            return json.dumps({"error": "Prometheus request timed out"})
        except httpx.ConnectError as e:
            return json.dumps({"error": f"Cannot connect to Prometheus: {e}"})
        except Exception as e:
            logger.error("prometheus_error", error=str(e))
            return json.dumps({"error": f"Prometheus query failed: {e}"})

    def _format_results(self, data: dict) -> dict:
        """Parse and format Prometheus query results."""
        status = data.get("status", "error")
        if status != "success":
            return {"error": data.get("error", "Unknown error"), "errorType": data.get("errorType")}

        result_data = data.get("data", {})
        result_type = result_data.get("resultType", "")
        results = result_data.get("result", [])

        formatted = []
        for item in results:
            metric = item.get("metric", {})
            entry: dict[str, Any] = {"metric": metric}

            if result_type == "vector":
                value = item.get("value", [])
                if len(value) == 2:
                    entry["timestamp"] = value[0]
                    entry["value"] = value[1]

            elif result_type == "matrix":
                values = item.get("values", [])
                entry["values"] = [
                    {"timestamp": v[0], "value": v[1]}
                    for v in values
                ]
                entry["sample_count"] = len(values)

            elif result_type == "scalar":
                value = item if isinstance(item, list) else item.get("value", [])
                if len(value) == 2:
                    entry["timestamp"] = value[0]
                    entry["value"] = value[1]

            formatted.append(entry)

        return {
            "status": "success",
            "result_type": result_type,
            "result_count": len(formatted),
            "results": formatted,
        }

    async def _query(self, base_url: str, kwargs: dict) -> str:
        promql = kwargs.get("promql", "")
        if not promql:
            return json.dumps({"error": "promql is required for query action"})

        url = f"{base_url}/api/v1/query"
        params = {"query": promql}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        result = self._format_results(data)
        logger.info("prometheus_query_done", result_count=result.get("result_count", 0))
        return _truncate(json.dumps(result))

    async def _query_range(self, base_url: str, kwargs: dict) -> str:
        promql = kwargs.get("promql", "")
        start = kwargs.get("start", "")
        end = kwargs.get("end", "")
        step = kwargs.get("step", "1m")

        if not promql:
            return json.dumps({"error": "promql is required"})
        if not start or not end:
            return json.dumps({"error": "start and end are required for query_range"})

        url = f"{base_url}/api/v1/query_range"
        params = {
            "query": promql,
            "start": start,
            "end": end,
            "step": step,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

        result = self._format_results(data)
        logger.info("prometheus_range_query_done", result_count=result.get("result_count", 0))
        return _truncate(json.dumps(result))

    async def _alerts(self, base_url: str) -> str:
        url = f"{base_url}/api/v1/alerts"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "success":
            return json.dumps({"error": data.get("error", "Failed to fetch alerts")})

        alerts = data.get("data", {}).get("alerts", [])
        formatted = [
            {
                "labels": a.get("labels", {}),
                "annotations": a.get("annotations", {}),
                "state": a.get("state", ""),
                "activeAt": a.get("activeAt", ""),
                "value": a.get("value", ""),
            }
            for a in alerts
        ]

        logger.info("prometheus_alerts_fetched", count=len(formatted))
        return _truncate(json.dumps({
            "alerts": formatted,
            "total": len(formatted),
            "firing": sum(1 for a in formatted if a["state"] == "firing"),
            "pending": sum(1 for a in formatted if a["state"] == "pending"),
        }))

    async def _targets(self, base_url: str) -> str:
        url = f"{base_url}/api/v1/targets"

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        if data.get("status") != "success":
            return json.dumps({"error": data.get("error", "Failed to fetch targets")})

        active = data.get("data", {}).get("activeTargets", [])
        dropped = data.get("data", {}).get("droppedTargets", [])

        formatted_active = [
            {
                "labels": t.get("labels", {}),
                "scrapeUrl": t.get("scrapeUrl", ""),
                "health": t.get("health", ""),
                "lastScrape": t.get("lastScrape", ""),
                "lastScrapeDuration": t.get("lastScrapeDuration", ""),
                "lastError": t.get("lastError", ""),
            }
            for t in active
        ]

        up_count = sum(1 for t in formatted_active if t["health"] == "up")

        logger.info("prometheus_targets_fetched", active=len(active), dropped=len(dropped))
        return _truncate(json.dumps({
            "active_targets": formatted_active,
            "active_count": len(formatted_active),
            "up_count": up_count,
            "down_count": len(formatted_active) - up_count,
            "dropped_count": len(dropped),
        }))
