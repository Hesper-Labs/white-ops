"""Circuit breaker service - distributed circuit breaker pattern using Redis."""

import time
from datetime import UTC, datetime

import redis.asyncio as aioredis
import structlog

from app.config import settings

logger = structlog.get_logger()

# Circuit states
STATE_CLOSED = "closed"      # Healthy: requests pass through
STATE_OPEN = "open"          # Failing: requests are blocked
STATE_HALF_OPEN = "half_open"  # Testing: limited requests allowed

# Default configuration
DEFAULT_FAILURE_THRESHOLD = 5      # Open after N failures
DEFAULT_RECOVERY_TIMEOUT = 60      # Seconds before transitioning from open to half_open
DEFAULT_SUCCESS_THRESHOLD = 3      # Close after N successes in half_open
DEFAULT_WINDOW_SECONDS = 120       # Sliding window for failure counting


class CircuitBreakerService:
    """Distributed circuit breaker using Redis for state storage.

    States:
    - closed (healthy): requests flow normally, failures are counted
    - open (failing): requests are blocked, transitions to half_open after recovery timeout
    - half_open (testing): limited requests allowed, successes close the circuit,
      failures reopen it
    """

    def __init__(self):
        self._redis: aioredis.Redis | None = None

    async def _get_redis(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = aioredis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=0,
                decode_responses=True,
            )
        return self._redis

    # ------------------------------------------------------------------
    # Key helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _key(service_name: str, suffix: str) -> str:
        return f"circuit:{service_name}:{suffix}"

    # ------------------------------------------------------------------
    # Core operations
    # ------------------------------------------------------------------

    async def check(self, service_name: str) -> bool:
        """Check whether a request should be allowed (True = circuit closed/half-open, allow request)."""
        r = await self._get_redis()
        state = await r.get(self._key(service_name, "state")) or STATE_CLOSED

        if state == STATE_CLOSED:
            return True

        if state == STATE_OPEN:
            # Check if recovery timeout has elapsed
            last_failure_ts = await r.get(self._key(service_name, "last_failure_ts"))
            recovery_timeout = int(await r.get(self._key(service_name, "recovery_timeout")) or DEFAULT_RECOVERY_TIMEOUT)

            if last_failure_ts:
                elapsed = time.time() - float(last_failure_ts)
                if elapsed >= recovery_timeout:
                    # Transition to half_open
                    await r.set(self._key(service_name, "state"), STATE_HALF_OPEN)
                    await r.set(self._key(service_name, "half_open_successes"), 0)
                    logger.info("circuit_half_open", service=service_name)
                    return True

            return False

        if state == STATE_HALF_OPEN:
            return True

        return True

    async def record_success(self, service_name: str) -> None:
        """Record a successful request."""
        r = await self._get_redis()
        state = await r.get(self._key(service_name, "state")) or STATE_CLOSED

        if state == STATE_HALF_OPEN:
            successes = await r.incr(self._key(service_name, "half_open_successes"))
            success_threshold = int(
                await r.get(self._key(service_name, "success_threshold")) or DEFAULT_SUCCESS_THRESHOLD
            )

            if successes >= success_threshold:
                # Close the circuit
                await self._transition(r, service_name, STATE_CLOSED)
                logger.info("circuit_closed", service=service_name, reason="success_threshold_reached")

        elif state == STATE_CLOSED:
            # Track success for metrics
            await r.incr(self._key(service_name, "total_successes"))

    async def record_failure(self, service_name: str) -> None:
        """Record a failed request."""
        r = await self._get_redis()
        state = await r.get(self._key(service_name, "state")) or STATE_CLOSED
        now = time.time()

        if state == STATE_HALF_OPEN:
            # Any failure in half_open reopens the circuit
            await self._transition(r, service_name, STATE_OPEN)
            await r.set(self._key(service_name, "last_failure_ts"), str(now))
            logger.warning("circuit_reopened", service=service_name, reason="half_open_failure")
            return

        # Increment failure count within the sliding window
        failures = await r.incr(self._key(service_name, "failures"))
        window = int(await r.get(self._key(service_name, "window")) or DEFAULT_WINDOW_SECONDS)

        # Set expiry on the failures counter to implement sliding window
        if failures == 1:
            await r.expire(self._key(service_name, "failures"), window)

        await r.set(self._key(service_name, "last_failure_ts"), str(now))
        await r.incr(self._key(service_name, "total_failures"))

        failure_threshold = int(
            await r.get(self._key(service_name, "failure_threshold")) or DEFAULT_FAILURE_THRESHOLD
        )

        if failures >= failure_threshold:
            await self._transition(r, service_name, STATE_OPEN)
            logger.warning(
                "circuit_opened",
                service=service_name,
                failures=failures,
                threshold=failure_threshold,
            )

    async def _transition(self, r: aioredis.Redis, service_name: str, new_state: str) -> None:
        """Transition a circuit to a new state."""
        await r.set(self._key(service_name, "state"), new_state)

        if new_state == STATE_CLOSED:
            await r.delete(self._key(service_name, "failures"))
            await r.delete(self._key(service_name, "half_open_successes"))
        elif new_state == STATE_OPEN:
            await r.delete(self._key(service_name, "half_open_successes"))

    # ------------------------------------------------------------------
    # State inspection
    # ------------------------------------------------------------------

    async def get_state(self, service_name: str) -> dict:
        """Get the current state of a circuit breaker."""
        r = await self._get_redis()

        state = await r.get(self._key(service_name, "state")) or STATE_CLOSED
        failures = int(await r.get(self._key(service_name, "failures")) or 0)
        total_successes = int(await r.get(self._key(service_name, "total_successes")) or 0)
        total_failures = int(await r.get(self._key(service_name, "total_failures")) or 0)
        last_failure_ts = await r.get(self._key(service_name, "last_failure_ts"))

        total = total_successes + total_failures
        success_rate = (total_successes / total * 100) if total > 0 else 100.0

        return {
            "service": service_name,
            "state": state,
            "failure_count": failures,
            "total_successes": total_successes,
            "total_failures": total_failures,
            "success_rate": round(success_rate, 2),
            "last_failure": datetime.fromtimestamp(float(last_failure_ts), tz=UTC).isoformat()
            if last_failure_ts else None,
        }

    async def get_all_states(self) -> list[dict]:
        """Get the state of all known circuit breakers."""
        r = await self._get_redis()

        # Scan for all circuit breaker state keys
        services: set[str] = set()
        async for key in r.scan_iter("circuit:*:state"):
            # key format: circuit:{service_name}:state
            parts = key.split(":")
            if len(parts) == 3:
                services.add(parts[1])

        states = []
        for service in sorted(services):
            state = await self.get_state(service)
            states.append(state)

        return states

    # ------------------------------------------------------------------
    # Manual controls
    # ------------------------------------------------------------------

    async def force_open(self, service_name: str) -> None:
        """Manually open a circuit breaker (block all requests)."""
        r = await self._get_redis()
        await self._transition(r, service_name, STATE_OPEN)
        await r.set(self._key(service_name, "last_failure_ts"), str(time.time()))
        logger.warning("circuit_force_opened", service=service_name)

    async def force_close(self, service_name: str) -> None:
        """Manually close a circuit breaker (allow all requests)."""
        r = await self._get_redis()
        await self._transition(r, service_name, STATE_CLOSED)
        logger.info("circuit_force_closed", service=service_name)

    async def reset(self, service_name: str) -> None:
        """Fully reset a circuit breaker, clearing all state."""
        r = await self._get_redis()

        keys_to_delete = [
            self._key(service_name, suffix)
            for suffix in [
                "state", "failures", "last_failure_ts", "half_open_successes",
                "total_successes", "total_failures", "failure_threshold",
                "recovery_timeout", "success_threshold", "window",
            ]
        ]
        if keys_to_delete:
            await r.delete(*keys_to_delete)

        logger.info("circuit_reset", service=service_name)


circuit_breaker = CircuitBreakerService()
