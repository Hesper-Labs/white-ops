from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import make_asgi_app

from app.config import settings as app_settings
from app.core.logging import setup_logging
from app.core.middleware import setup_middleware
from app.db.session import engine
from app.db.init_db import init_db
from app.api.v1 import (
    auth, agents, tasks, workflows, admin, files, messages,
    dashboard, settings, workers, knowledge, collaboration, analytics,
    schedules, exports,
)
from app.api.websocket import router as ws_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    setup_logging(
        log_level="DEBUG" if app_settings.debug else "INFO",
        json_output=not app_settings.debug,
    )
    logger.info("server_starting", env=app_settings.app_env)
    await init_db()
    logger.info("database_initialized")
    yield
    await engine.dispose()
    logger.info("server_stopped")


app = FastAPI(
    title="White-Ops API",
    description="AI-Powered White-Collar Workforce Platform",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if app_settings.debug else None,
    redoc_url="/redoc" if app_settings.debug else None,
)

# CORS - restricted for production
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

# Production middleware (rate limiting, logging, security headers)
setup_middleware(app)

# Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# API routes
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(agents.router, prefix="/api/v1/agents", tags=["agents"])
app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["workflows"])
app.include_router(admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(files.router, prefix="/api/v1/files", tags=["files"])
app.include_router(messages.router, prefix="/api/v1/messages", tags=["messages"])
app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
app.include_router(settings.router, prefix="/api/v1/settings", tags=["settings"])
app.include_router(workers.router, prefix="/api/v1/workers", tags=["workers"])
app.include_router(knowledge.router, prefix="/api/v1/knowledge", tags=["knowledge"])
app.include_router(collaboration.router, prefix="/api/v1/collaboration", tags=["collaboration"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(schedules.router, prefix="/api/v1/schedules", tags=["schedules"])
app.include_router(exports.router, prefix="/api/v1/exports", tags=["exports"])
app.include_router(ws_router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "healthy", "service": "white-ops-server", "version": "0.1.0"}
