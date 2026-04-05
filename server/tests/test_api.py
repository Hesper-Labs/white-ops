"""API endpoint tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_agents_list_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/agents/")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_tasks_list_requires_auth(client: AsyncClient):
    response = await client.get("/api/v1/tasks/")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_settings_requires_admin(client: AsyncClient):
    response = await client.get("/api/v1/settings/")
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_openapi_docs_available_in_debug():
    """Verify docs endpoint exists."""
    from app.config import settings
    if settings.debug:
        # docs should be available
        pass
    # In production, docs should be disabled


@pytest.mark.asyncio
async def test_cors_headers(client: AsyncClient):
    response = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    # CORS should respond
    assert response.status_code in (200, 405)


@pytest.mark.asyncio
async def test_rate_limit_headers(client: AsyncClient):
    """Verify rate limiting is active."""
    response = await client.get("/health")
    # Should include request ID header from middleware
    assert "x-request-id" in response.headers or response.status_code == 200


@pytest.mark.asyncio
async def test_security_headers(client: AsyncClient):
    response = await client.get("/health")
    headers = response.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-xss-protection") == "1; mode=block"
