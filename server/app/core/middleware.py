"""Production middleware: Redis rate limiting, request logging, security headers, error handling."""

import collections
import threading
import time
import uuid

import redis.asyncio as aioredis
import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from jose import JWTError
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings

logger = structlog.get_logger()

# Redis client initialized in setup_middleware()
_redis: aioredis.Redis | None = None

# ---- Rate Limiter (Redis sliding window) ----

# Per-endpoint rate limit overrides: path prefix -> (limit, window_seconds)
ENDPOINT_RATE_LIMITS: dict[str, tuple[int, int]] = {
    "/api/v1/auth/login": (20, 60),
    "/api/v1/auth/register": (10, 60),
    "/api/v1/auth/forgot-password": (5, 60),
}

SKIP_PATHS = frozenset(("/health", "/docs", "/openapi.json", "/redoc"))

_memory_rate_store: dict[str, collections.deque] = {}
_memory_rate_lock = threading.Lock()
_MAX_MEMORY_KEYS = 10000  # Prevent unbounded memory growth


def _in_memory_rate_check(key: str, limit: int, window: int) -> tuple[bool, int, int]:
    """In-memory sliding-window rate limiter as fallback when Redis is unavailable."""
    now = time.time()
    reset_at = int(now) + window

    with _memory_rate_lock:
        # Evict stale keys if store is too large
        if len(_memory_rate_store) > _MAX_MEMORY_KEYS:
            cutoff = now - window * 2
            stale_keys = [k for k, v in _memory_rate_store.items() if not v or v[-1] < cutoff]
            for k in stale_keys[:1000]:
                del _memory_rate_store[k]

        if key not in _memory_rate_store:
            _memory_rate_store[key] = collections.deque()

        dq = _memory_rate_store[key]

        # Remove expired entries
        window_start = now - window
        while dq and dq[0] < window_start:
            dq.popleft()

        # Add current request
        dq.append(now)

        current_count = len(dq)
        allowed = current_count <= limit
        remaining = max(0, limit - current_count)

    return allowed, remaining, reset_at


async def _redis_sliding_window(key: str, limit: int, window: int) -> tuple[bool, int, int]:
    """Check rate limit using Redis sorted-set sliding window.

    Returns (allowed, remaining, reset_epoch).
    """
    now = time.time()
    window_start = now - window
    reset_at = int(now) + window
    pipe = _redis.pipeline()
    # Remove expired entries
    pipe.zremrangebyscore(key, 0, window_start)
    # Add current request
    pipe.zadd(key, {f"{now}:{uuid.uuid4().hex[:8]}": now})
    # Count requests in window
    pipe.zcard(key)
    # Set TTL so keys auto-expire
    pipe.expire(key, window + 1)
    results = await pipe.execute()
    current_count = results[2]
    allowed = current_count <= limit
    remaining = max(0, limit - current_count)
    return allowed, remaining, reset_at


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in SKIP_PATHS:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"

        # Determine rate limit tier: per-user (JWT) > per-endpoint > per-IP default
        limit, window = 120, 60
        rate_key = f"rl:ip:{client_ip}"

        # Check for per-endpoint override
        for prefix, (ep_limit, ep_window) in ENDPOINT_RATE_LIMITS.items():
            if request.url.path.startswith(prefix):
                limit, window = ep_limit, ep_window
                rate_key = f"rl:ep:{client_ip}:{prefix}"
                break

        # Per-user rate limit (higher) if JWT present
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_access_token

                payload = decode_access_token(auth_header[7:])
                user_id = payload.get("sub")
                if user_id:
                    limit, window = 300, 60
                    rate_key = f"rl:user:{user_id}"
            except Exception:
                pass  # Fall back to IP-based limiting

        # Try Redis, fall back to in-memory rate limiting on failure
        if _redis is not None:
            try:
                allowed, remaining, reset_at = await _redis_sliding_window(
                    rate_key, limit, window
                )
            except Exception as exc:
                logger.warning("redis_rate_limit_error", error=str(exc))
                allowed, remaining, reset_at = _in_memory_rate_check(rate_key, limit, window)
        else:
            logger.warning("redis_unavailable_using_memory_rate_limit")
            allowed, remaining, reset_at = _in_memory_rate_check(rate_key, limit, window)

        if not allowed:
            logger.warning("rate_limit_exceeded", key=rate_key, path=request.url.path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(reset_at),
                },
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at)
        return response


# ---- Request Logging ----

DEFAULT_MAX_BODY_SIZE = 10 * 1024 * 1024  # 10 MB


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_body_size: int = DEFAULT_MAX_BODY_SIZE) -> None:
        super().__init__(app)
        self.max_body_size = max_body_size

    async def dispatch(self, request: Request, call_next) -> Response:
        # Reject oversized request bodies
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.max_body_size:
            return JSONResponse(
                status_code=413,
                content={
                    "detail": f"Request body too large. Maximum size is {self.max_body_size} bytes."
                },
            )

        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Extract user_id from auth token if present
        user_id = None
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from app.core.security import decode_access_token

                payload = decode_access_token(auth_header[7:])
                user_id = payload.get("sub")
            except Exception:
                pass

        # Bind request context
        structlog.contextvars.clear_contextvars()
        ctx = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        }
        if user_id:
            ctx["user_id"] = user_id
        structlog.contextvars.bind_contextvars(**ctx)

        try:
            response = await call_next(request)
            duration_ms = round((time.time() - start_time) * 1000, 1)

            if request.url.path not in ("/health", "/ws"):
                logger.info(
                    "request_completed",
                    status=response.status_code,
                    duration_ms=duration_ms,
                    client=request.client.host if request.client else "unknown",
                )

            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms}ms"
            return response

        except Exception as e:
            duration_ms = round((time.time() - start_time) * 1000, 1)
            logger.error(
                "request_failed",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=duration_ms,
            )
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "request_id": request_id},
            )


# ---- Security Headers ----


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        # Additional security headers
        response.headers["Strict-Transport-Security"] = (
            "max-age=63072000; includeSubDomains; preload"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; font-src 'self'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
        return response


# ---- Global Exception Handlers ----


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


async def validation_exception_handler(
    request: Request, exc: ValidationError
) -> JSONResponse:
    logger.warning(
        "validation_error",
        error=str(exc),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": exc.errors()},
    )


async def sqlalchemy_exception_handler(
    request: Request, exc: SQLAlchemyError
) -> JSONResponse:
    logger.error(
        "database_error",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "A database error occurred. Please try again later."},
    )


async def jwt_exception_handler(request: Request, exc: JWTError) -> JSONResponse:
    logger.warning(
        "jwt_error",
        error=str(exc),
        path=request.url.path,
    )
    return JSONResponse(
        status_code=401,
        content={"detail": "Invalid or expired authentication token."},
    )


# ---- Setup ----


async def setup_middleware(app: FastAPI) -> None:
    """Register all production middleware and initialize Redis for rate limiting."""
    global _redis

    # Initialize Redis connection for rate limiting
    try:
        _redis = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
        await _redis.ping()
        logger.info("redis_connected", purpose="rate_limiting")
    except Exception as exc:
        logger.warning(
            "redis_connection_failed",
            error=str(exc),
            detail="Rate limiting will be disabled until Redis is available.",
        )
        _redis = None

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RateLimitMiddleware)

    # Exception handlers
    app.add_exception_handler(Exception, global_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_exception_handler)
    app.add_exception_handler(JWTError, jwt_exception_handler)
