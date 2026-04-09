"""HTTP API caller tool - make requests to external REST APIs with auth support."""

import ipaddress
import json
from base64 import b64encode
from typing import Any
from urllib.parse import urlparse

import httpx
import structlog

from agent.tools.base import BaseTool

logger = structlog.get_logger()

MAX_OUTPUT_BYTES = 50 * 1024
MAX_RESPONSE_SIZE = 1 * 1024 * 1024  # 1MB
DEFAULT_TIMEOUT = 30
MAX_TIMEOUT = 120

# Private/internal IP ranges that are blocked by default
PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_BYTES:
        return text[:MAX_OUTPUT_BYTES] + "\n... [output truncated]"
    return text


def _is_private_ip(hostname: str) -> bool:
    """Check if hostname resolves to a private IP, including DNS resolution."""
    import socket

    if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        return True
    try:
        addr = ipaddress.ip_address(hostname)
        return any(addr in network for network in PRIVATE_RANGES)
    except ValueError:
        pass

    # Resolve hostname to check if it points to a private IP
    try:
        addrinfos = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in addrinfos:
            ip_str = sockaddr[0]
            try:
                addr = ipaddress.ip_address(ip_str)
                if any(addr in network for network in PRIVATE_RANGES):
                    return True
            except ValueError:
                continue
    except socket.gaierror:
        pass

    return False


# AWS/GCP/Azure metadata endpoints
BLOCKED_METADATA_IPS = {
    "169.254.169.254",  # AWS/GCP metadata
    "metadata.google.internal",
    "169.254.170.2",    # AWS ECS task metadata
}


class APICallerTool(BaseTool):
    name = "api_caller"
    description = (
        "Make HTTP requests to external REST APIs. Supports GET, POST, PUT, "
        "PATCH, DELETE with bearer, basic, and API key authentication. "
        "Blocks requests to localhost and private IPs unless explicitly allowed."
    )
    parameters = {
        "type": "object",
        "properties": {
            "method": {
                "type": "string",
                "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"],
                "description": "HTTP method.",
            },
            "url": {
                "type": "string",
                "description": "Request URL.",
            },
            "headers": {
                "type": "object",
                "description": "HTTP headers as key-value pairs.",
                "additionalProperties": {"type": "string"},
            },
            "body": {
                "type": "object",
                "description": "JSON request body (for POST, PUT, PATCH).",
            },
            "form_data": {
                "type": "object",
                "description": "Form data (application/x-www-form-urlencoded).",
                "additionalProperties": {"type": "string"},
            },
            "auth": {
                "type": "object",
                "description": "Authentication configuration.",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["bearer", "basic", "api_key"],
                    },
                    "token": {"type": "string", "description": "Token for bearer auth."},
                    "username": {"type": "string", "description": "Username for basic auth."},
                    "password": {"type": "string", "description": "Password for basic auth."},
                    "key": {"type": "string", "description": "API key value."},
                    "header_name": {
                        "type": "string",
                        "description": "Header name for api_key auth. Default: X-API-Key.",
                    },
                    "in_query": {
                        "type": "string",
                        "description": "Query parameter name for api_key auth (instead of header).",
                    },
                },
            },
            "params": {
                "type": "object",
                "description": "URL query parameters.",
                "additionalProperties": {"type": "string"},
            },
            "timeout": {
                "type": "integer",
                "description": f"Request timeout in seconds. Default: {DEFAULT_TIMEOUT}, max: {MAX_TIMEOUT}.",
            },
            "allow_internal": {
                "type": "boolean",
                "description": "Allow requests to localhost/private IPs. Default: false.",
            },
        },
        "required": ["method", "url"],
    }

    def _apply_auth(self, headers: dict, params: dict, auth: dict | None) -> None:
        """Apply authentication to headers or params."""
        if not auth:
            return

        auth_type = auth.get("type", "")

        if auth_type == "bearer":
            token = auth.get("token", "")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif auth_type == "basic":
            username = auth.get("username", "")
            password = auth.get("password", "")
            encoded = b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"

        elif auth_type == "api_key":
            key = auth.get("key", "")
            in_query = auth.get("in_query")
            if in_query:
                params[in_query] = key
            else:
                header_name = auth.get("header_name", "X-API-Key")
                headers[header_name] = key

    async def execute(self, **kwargs: Any) -> Any:
        method = kwargs.get("method", "GET")
        url = kwargs.get("url", "")
        logger.info("api_caller_execute", method=method, url=url)

        if not url:
            return json.dumps({"error": "url is required"})

        # Validate URL
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return json.dumps({"error": f"Unsupported scheme: {parsed.scheme}. Use http or https."})

        # Block cloud metadata endpoints (always blocked, even with allow_internal)
        hostname = parsed.hostname or ""
        if hostname in BLOCKED_METADATA_IPS:
            return json.dumps({
                "error": "Requests to cloud metadata endpoints are always blocked for security."
            })

        # Check for private IPs (with DNS resolution)
        allow_internal = kwargs.get("allow_internal", False)
        if not allow_internal and _is_private_ip(hostname):
            return json.dumps({
                "error": "Requests to localhost/private IPs are blocked. Set allow_internal=true to override."
            })

        # Prepare request
        headers = dict(kwargs.get("headers") or {})
        params = dict(kwargs.get("params") or {})
        body = kwargs.get("body")
        form_data = kwargs.get("form_data")
        auth = kwargs.get("auth")
        timeout = min(kwargs.get("timeout", DEFAULT_TIMEOUT), MAX_TIMEOUT)

        self._apply_auth(headers, params, auth)

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=False,
                max_redirects=0,
            ) as client:
                request_kwargs: dict[str, Any] = {
                    "method": method,
                    "url": url,
                    "headers": headers,
                    "params": params if params else None,
                }

                if body and method in ("POST", "PUT", "PATCH"):
                    request_kwargs["json"] = body
                elif form_data and method in ("POST", "PUT", "PATCH"):
                    request_kwargs["data"] = form_data

                response = await client.request(**request_kwargs)

            # Handle redirects safely - check target for SSRF
            if response.is_redirect:
                location = response.headers.get("location", "")
                if location:
                    redirect_parsed = urlparse(location)
                    redirect_host = redirect_parsed.hostname or ""
                    if redirect_host in BLOCKED_METADATA_IPS:
                        return json.dumps({
                            "error": "Redirect to cloud metadata endpoint blocked."
                        })
                    if not allow_internal and _is_private_ip(redirect_host):
                        return json.dumps({
                            "error": f"Redirect to private IP blocked: {redirect_host}"
                        })
                    return json.dumps({
                        "redirect": True,
                        "status_code": response.status_code,
                        "location": location,
                        "message": "Request was redirected. Make a new request to the location URL.",
                    })

            # Check response size
            content_length = int(response.headers.get("content-length", 0))
            if content_length > MAX_RESPONSE_SIZE:
                return json.dumps({
                    "error": f"Response too large: {content_length} bytes (max {MAX_RESPONSE_SIZE})"
                })

            # Parse response
            try:
                response_body = response.json()
            except Exception:
                text = response.text
                if len(text) > MAX_RESPONSE_SIZE:
                    text = text[:MAX_RESPONSE_SIZE] + "... [truncated]"
                response_body = text

            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "body": response_body,
                "elapsed_ms": int(response.elapsed.total_seconds() * 1000),
            }

            logger.info(
                "api_caller_done",
                status=response.status_code,
                elapsed_ms=result["elapsed_ms"],
            )
            return _truncate(json.dumps(result, ensure_ascii=False, default=str))

        except httpx.TimeoutException:
            logger.error("api_caller_timeout", url=url, timeout=timeout)
            return json.dumps({"error": f"Request timed out after {timeout}s"})
        except httpx.ConnectError as e:
            return json.dumps({"error": f"Connection failed: {e}"})
        except Exception as e:
            logger.error("api_caller_error", error=str(e))
            return json.dumps({"error": f"Request failed: {e}"})
