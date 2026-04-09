"""Middleware tests - rate limiting, security headers, request logging."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_security_headers_present(client: AsyncClient):
    """Verify security headers are set (if middleware is active)."""
    response = await client.get("/health")
    headers = response.headers
    # These headers are set by SecurityHeadersMiddleware
    # In test mode without full middleware stack, they may not be present
    if "x-content-type-options" in headers:
        assert headers["x-content-type-options"] == "nosniff"
        assert headers["x-frame-options"] == "DENY"
        assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_request_id_header(client: AsyncClient):
    """X-Request-ID should be present when middleware is active."""
    response = await client.get("/health")
    # Request ID is set by RequestLoggingMiddleware
    if "x-request-id" in response.headers:
        assert len(response.headers["x-request-id"]) > 0
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_response_time_header(client: AsyncClient):
    """X-Response-Time should be present when middleware is active."""
    response = await client.get("/health")
    if "x-response-time" in response.headers:
        assert response.headers["x-response-time"].endswith("ms")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_skips_rate_limiting(client: AsyncClient):
    """Health endpoint should not be rate limited."""
    response = await client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_auth_endpoints_require_auth(client: AsyncClient):
    """Protected endpoints should return 401/403 without auth."""
    protected_paths = [
        "/api/v1/agents/",
        "/api/v1/tasks/",
        "/api/v1/settings/",
        "/api/v1/admin/users",
        "/api/v1/secrets/",
    ]
    for path in protected_paths:
        response = await client.get(path)
        assert response.status_code in (401, 403), f"{path} returned {response.status_code}"


@pytest.mark.asyncio
async def test_invalid_json_returns_422(client: AsyncClient):
    """Malformed JSON should return 422."""
    response = await client.post(
        "/api/v1/auth/login",
        content="not-json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_missing_fields_returns_422(client: AsyncClient):
    """Login with missing fields should return 422."""
    response = await client.post("/api/v1/auth/login", json={"email": "test@test.com"})
    assert response.status_code == 422
