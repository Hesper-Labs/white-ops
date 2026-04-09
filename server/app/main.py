"""White-Ops API Server - Enterprise AI Workforce Platform."""

import asyncio
import signal
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1 import (
    admin,
    agents,
    analytics,
    approvals,
    auth,
    chat,
    circuit_breakers,
    code_reviews,
    collaboration,
    cost,
    dashboard,
    dead_letter,
    exports,
    files,
    knowledge,
    marketplace,
    memories,
    messages,
    notifications,
    schedules,
    secrets,
    # Enterprise modules
    security,
    settings,
    ssh_connections,
    tasks,
    triggers,
    webhooks,
    workers,
    workflows,
)
from app.api.websocket import router as ws_router
from app.config import settings as app_settings
from app.core.errors import AppException, ErrorCode
from app.core.logging import setup_logging
from app.core.middleware import setup_middleware
from app.db.init_db import init_db
from app.db.session import engine

logger = structlog.get_logger()

APP_VERSION = "1.0.0"

# Graceful shutdown event
_shutdown_event = asyncio.Event()


def _handle_signal(sig: signal.Signals) -> None:
    """Handle termination signals for graceful shutdown."""
    logger.info("shutdown_signal_received", signal=sig.name)
    _shutdown_event.set()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifecycle: startup validation, init, and graceful shutdown."""
    # Setup logging first
    setup_logging(
        log_level="DEBUG" if app_settings.debug else "INFO",
        json_output=not app_settings.debug,
    )

    logger.info(
        "server_starting",
        env=app_settings.app_env,
        version=APP_VERSION,
        debug=app_settings.debug,
    )

    # Register signal handlers for graceful shutdown
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, _handle_signal, sig)

    # Initialize database
    await init_db()
    logger.info("database_initialized")

    # Initialize middleware (Redis connections for rate limiting)
    await setup_middleware(app)
    logger.info("middleware_initialized")

    logger.info("server_ready", version=APP_VERSION)

    yield

    # Graceful shutdown: wait for in-flight requests (max 30s)
    logger.info("server_shutting_down", message="Draining in-flight requests...")
    _shutdown_event.set()

    await engine.dispose()
    logger.info("database_connections_closed")
    logger.info("server_stopped")


app = FastAPI(
    title="White-Ops API",
    description="Enterprise AI Workforce Platform",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Insufficient permissions"},
        404: {"description": "Resource not found"},
        422: {"description": "Validation error"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization", "Content-Type", "X-Request-ID",
        "X-API-Key", "Accept", "Origin",
    ],
    expose_headers=[
        "X-Request-ID", "X-Response-Time",
        "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset",
    ],
)

# ---- Prometheus Metrics ----
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)


# ---- Exception Handlers ----

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle structured application errors."""
    logger.warning(
        "app_error",
        error_code=exc.error_code.value,
        message=exc.message,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return structured validation errors with error codes."""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"],
        })
    return JSONResponse(
        status_code=422,
        content={
            "error_code": ErrorCode.VALIDATION_ERROR.value,
            "error_name": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": {"errors": errors},
        },
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle database errors without leaking internals."""
    logger.error("database_error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=500,
        content={
            "error_code": ErrorCode.DATABASE_ERROR.value,
            "error_name": "DATABASE_ERROR",
            "message": "A database error occurred. Please try again.",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={
            "error_code": ErrorCode.INTERNAL_ERROR.value,
            "error_name": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Please try again.",
        },
    )


# ---- Core API Routes ----
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["Tasks"])
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["Workflows"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
app.include_router(files.router, prefix="/api/v1/files", tags=["Files"])
app.include_router(messages.router, prefix="/api/v1/messages", tags=["Messages"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["Dashboard"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["Settings"])
app.include_router(workers.router, prefix="/api/v1/workers", tags=["Workers"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["Knowledge Base"])
app.include_router(collaboration.router, prefix="/api/v1/collaboration", tags=["Collaboration"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(schedules.router, prefix="/api/v1/schedules", tags=["Schedules"])
app.include_router(exports.router, prefix="/api/v1/exports", tags=["Import/Export"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])

# ---- Enterprise API Routes ----
app.include_router(security.router, prefix="/api/v1/security", tags=["Security"])
app.include_router(secrets.router, prefix="/api/v1/secrets", tags=["Secrets Vault"])
app.include_router(ssh_connections.router, prefix="/api/v1/ssh-connections", tags=["SSH Connections"])
app.include_router(approvals.router, prefix="/api/v1/approvals", tags=["Approvals"])
app.include_router(memories.router, prefix="/api/v1/agents", tags=["Agent Intelligence"])
app.include_router(dead_letter.router, prefix="/api/v1/dead-letter", tags=["Dead Letter Queue"])
app.include_router(cost.router, prefix="/api/v1/cost", tags=["Cost Management"])
app.include_router(triggers.router, prefix="/api/v1/triggers", tags=["Triggers & Automation"])
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["Notifications"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])
app.include_router(circuit_breakers.router, prefix="/api/v1/circuit-breakers", tags=["Circuit Breakers"])
app.include_router(code_reviews.router, prefix="/api/v1/code-reviews", tags=["Code Reviews"])
app.include_router(marketplace.router, prefix="/api/v1/marketplace", tags=["Marketplace"])

# ---- WebSocket ----
app.include_router(ws_router)


# ---- Health & Readiness ----

@app.get("/health", tags=["System"])
async def health_check() -> dict:
    """Liveness probe - confirms the process is running."""
    return {
        "status": "healthy",
        "service": "white-ops-server",
        "version": APP_VERSION,
        "environment": app_settings.app_env,
    }


@app.get("/ready", tags=["System"])
async def readiness_check() -> JSONResponse:
    """Readiness probe - checks all critical dependencies."""
    checks: dict[str, str] = {}
    overall = "ready"

    # Check database
    try:
        from sqlalchemy import text

        from app.db.session import async_session_maker
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {type(e).__name__}"
        overall = "not_ready"

    # Check Redis
    try:
        import redis.asyncio as aioredis
        r = aioredis.from_url(app_settings.redis_url)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {type(e).__name__}"
        overall = "not_ready"

    # Check MinIO
    try:
        from minio import Minio
        client = Minio(
            app_settings.minio_endpoint,
            access_key=app_settings.minio_root_user,
            secret_key=app_settings.minio_root_password,
            secure=app_settings.minio_use_ssl,
        )
        client.list_buckets()
        checks["minio"] = "ok"
    except Exception as e:
        checks["minio"] = f"error: {type(e).__name__}"
        overall = "not_ready"

    status_code = 200 if overall == "ready" else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall,
            "version": APP_VERSION,
            "checks": checks,
        },
    )
