"""Health checker tool - check HTTP, TCP, and SSL endpoint health."""

import asyncio
import json
import ssl
import time
from datetime import datetime, timezone
from typing import Any

import httpx
import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
DEFAULT_TIMEOUT = 10


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_BYTES:
        return text[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
    return text


class HealthCheckerTool(BaseTool):
    name = "health_checker"
    description = (
        "Check health of HTTP endpoints, TCP ports, and SSL certificates. "
        "Supports parallel checks for multiple URLs and returns response times."
    )
    parameters = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["check_http", "check_tcp", "check_endpoints", "check_ssl"],
                "description": "Health check action to perform.",
            },
            "url": {
                "type": "string",
                "description": "URL to check (for check_http).",
            },
            "urls": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of URLs (for check_endpoints).",
            },
            "host": {
                "type": "string",
                "description": "Hostname (for check_tcp, check_ssl).",
            },
            "hostname": {
                "type": "string",
                "description": "Hostname for SSL check (alias for host).",
            },
            "port": {
                "type": "integer",
                "description": "Port number (for check_tcp). Default: 443 for check_ssl.",
            },
            "expected_status": {
                "type": "integer",
                "description": "Expected HTTP status code (for check_http). Default: 200.",
            },
            "timeout": {
                "type": "integer",
                "description": f"Timeout in seconds. Default: {DEFAULT_TIMEOUT}.",
            },
            "parallel": {
                "type": "boolean",
                "description": "Run checks in parallel (for check_endpoints). Default: true.",
            },
        },
        "required": ["action"],
    }

    async def execute(self, **kwargs: Any) -> Any:
        action = kwargs.get("action")
        logger.info("health_checker_execute", action=action)

        try:
            if action == "check_http":
                return await self._check_http(kwargs)
            elif action == "check_tcp":
                return await self._check_tcp(kwargs)
            elif action == "check_endpoints":
                return await self._check_endpoints(kwargs)
            elif action == "check_ssl":
                return await self._check_ssl(kwargs)
            else:
                return json.dumps({"error": f"Unknown action: {action}"})
        except Exception as e:
            logger.error("health_checker_error", error=str(e))
            return json.dumps({"error": f"Health check failed: {e}"})

    async def _check_http(self, kwargs: dict) -> str:
        url = kwargs.get("url", "")
        if not url:
            return json.dumps({"error": "url is required"})

        expected_status = kwargs.get("expected_status", 200)
        timeout = kwargs.get("timeout", DEFAULT_TIMEOUT)

        start = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                verify=True,
            ) as client:
                resp = await client.get(url)

            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            is_healthy = resp.status_code == expected_status

            result = {
                "url": url,
                "status": "healthy" if is_healthy else "unhealthy",
                "status_code": resp.status_code,
                "expected_status": expected_status,
                "response_time_ms": elapsed_ms,
                "content_length": len(resp.content),
            }

            logger.info("health_http_check", url=url, healthy=is_healthy, ms=elapsed_ms)
            return json.dumps(result)

        except httpx.TimeoutException:
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            return json.dumps({
                "url": url,
                "status": "unhealthy",
                "error": "timeout",
                "response_time_ms": elapsed_ms,
            })
        except httpx.ConnectError as e:
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            return json.dumps({
                "url": url,
                "status": "unhealthy",
                "error": f"connection_failed: {e}",
                "response_time_ms": elapsed_ms,
            })

    async def _check_tcp(self, kwargs: dict) -> str:
        host = kwargs.get("host", "")
        port = kwargs.get("port")

        if not host:
            return json.dumps({"error": "host is required"})
        if not port:
            return json.dumps({"error": "port is required"})

        timeout = kwargs.get("timeout", DEFAULT_TIMEOUT)

        start = time.monotonic()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout,
            )
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            writer.close()
            await writer.wait_closed()

            result = {
                "host": host,
                "port": port,
                "status": "healthy",
                "response_time_ms": elapsed_ms,
            }
            logger.info("health_tcp_check", host=host, port=port, healthy=True)
            return json.dumps(result)

        except asyncio.TimeoutError:
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            return json.dumps({
                "host": host,
                "port": port,
                "status": "unhealthy",
                "error": "timeout",
                "response_time_ms": elapsed_ms,
            })
        except (ConnectionRefusedError, OSError) as e:
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)
            return json.dumps({
                "host": host,
                "port": port,
                "status": "unhealthy",
                "error": str(e),
                "response_time_ms": elapsed_ms,
            })

    async def _check_endpoints(self, kwargs: dict) -> str:
        urls = kwargs.get("urls", [])
        if not urls:
            return json.dumps({"error": "urls list is required"})

        parallel = kwargs.get("parallel", True)
        timeout = kwargs.get("timeout", DEFAULT_TIMEOUT)

        async def check_one(url: str) -> dict:
            result_str = await self._check_http({
                "url": url,
                "timeout": timeout,
                "expected_status": kwargs.get("expected_status", 200),
            })
            return json.loads(result_str)

        if parallel:
            results = await asyncio.gather(
                *[check_one(url) for url in urls],
                return_exceptions=True,
            )
            # Handle any exceptions from gather
            processed = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    processed.append({
                        "url": urls[i],
                        "status": "unhealthy",
                        "error": str(result),
                    })
                else:
                    processed.append(result)
        else:
            processed = []
            for url in urls:
                result = await check_one(url)
                processed.append(result)

        healthy = sum(1 for r in processed if r.get("status") == "healthy")
        total = len(processed)

        logger.info("health_endpoints_check", total=total, healthy=healthy)
        return _truncate(json.dumps({
            "results": processed,
            "summary": {
                "total": total,
                "healthy": healthy,
                "unhealthy": total - healthy,
            },
        }))

    async def _check_ssl(self, kwargs: dict) -> str:
        hostname = kwargs.get("hostname") or kwargs.get("host", "")
        port = kwargs.get("port", 443)

        if not hostname:
            return json.dumps({"error": "hostname (or host) is required"})

        timeout = kwargs.get("timeout", DEFAULT_TIMEOUT)

        try:
            ctx = ssl.create_default_context()
            start = time.monotonic()

            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(hostname, port, ssl=ctx),
                timeout=timeout,
            )
            elapsed_ms = round((time.monotonic() - start) * 1000, 2)

            ssl_object = writer.get_extra_info("ssl_object")
            cert = ssl_object.getpeercert() if ssl_object else None

            writer.close()
            await writer.wait_closed()

            if not cert:
                return json.dumps({
                    "hostname": hostname,
                    "port": port,
                    "status": "unhealthy",
                    "error": "No certificate found",
                })

            # Parse expiry
            not_after = cert.get("notAfter", "")
            not_before = cert.get("notBefore", "")
            subject = dict(x[0] for x in cert.get("subject", []))
            issuer = dict(x[0] for x in cert.get("issuer", []))

            # Calculate days until expiry
            expiry_days = None
            if not_after:
                try:
                    expiry_dt = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
                    expiry_dt = expiry_dt.replace(tzinfo=timezone.utc)
                    delta = expiry_dt - datetime.now(timezone.utc)
                    expiry_days = delta.days
                except ValueError:
                    pass

            san = cert.get("subjectAltName", [])
            alt_names = [name for _, name in san]

            result = {
                "hostname": hostname,
                "port": port,
                "status": "healthy" if (expiry_days is not None and expiry_days > 0) else "unhealthy",
                "response_time_ms": elapsed_ms,
                "ssl_expiry_days": expiry_days,
                "not_before": not_before,
                "not_after": not_after,
                "subject": subject,
                "issuer": issuer,
                "alt_names": alt_names[:20],
                "protocol_version": ssl_object.version() if ssl_object else None,
            }

            logger.info("health_ssl_check", hostname=hostname, expiry_days=expiry_days)
            return json.dumps(result)

        except ssl.SSLCertVerificationError as e:
            return json.dumps({
                "hostname": hostname,
                "port": port,
                "status": "unhealthy",
                "error": f"SSL verification failed: {e}",
            })
        except asyncio.TimeoutError:
            return json.dumps({
                "hostname": hostname,
                "port": port,
                "status": "unhealthy",
                "error": "Connection timed out",
            })
        except Exception as e:
            return json.dumps({
                "hostname": hostname,
                "port": port,
                "status": "unhealthy",
                "error": str(e),
            })
