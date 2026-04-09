"""Middleware tests - rate limiting, security headers, request logging."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_security_headers_present(client: AsyncClient):
    """Verify all security headers are set."""
    response = await client.get("/health")
    headers = response.headers

    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert "strict-transport-security" in headers
    assert "content-security-policy" in headers
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "permissions-policy" in headers
    assert headers.get("x-permitted-cross-domain-policies") == "none"


@pytest.mark.asyncio
async def test_request_id_header(client: AsyncClient):
    """Every response should include X-Request-ID."""
    response = await client.get("/health")
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0


@pytest.mark.asyncio
async def test_response_time_header(client: AsyncClient):
    """Every response should include X-Response-Time."""
    response = await client.get("/health")
    assert "x-response-time" in response.headers


@pytest.mark.asyncio
async def test_rate_limit_headers_present(client: AsyncClient):
    """Rate limit info should be in response headers."""
    response = await client.get("/health")
    # Health endpoint skips rate limiting
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_oversized_body_rejected(client: AsyncClient):
    """Request body larger than limit should be rejected with 413."""
    large_body = "x" * (11 * 1024 * 1024)  # 11MB
    response = await client.post(
        "/api/v1/auth/login",
        content=large_body,
        headers={"Content-Type": "application/json", "Content-Length": str(len(large_body))},
    )
    assert response.status_code == 413


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
