"""Retry/backoff + circuit breaker. Pure stdlib; no sleeping in callers' handlers
(the client awaits asyncio.sleep, workers retry via ARQ)."""
from __future__ import annotations

import random
import time


def parse_retry_after(value: str | None) -> float | None:
    """Parse a Retry-After header (delta-seconds). HTTP-date form is not
    supported here; callers treat an unparseable value as absent."""
    if value is None:
        return None
    try:
        seconds = float(str(value).strip())
    except ValueError:
        return None
    return max(0.0, seconds)


def backoff_seconds(attempt: int, *, base: float = 1.0, cap: float = 60.0,
                    jitter: float = 0.25, rng=None) -> float:
    """Exponential backoff with full-ish jitter, bounded by `cap`.

    attempt is 0-based (first retry). Deterministic when rng is seeded.
    """
    raw = min(cap, base * (2 ** attempt))
    r = rng or random
    return raw * (1.0 + r.uniform(-jitter, jitter)) if jitter else raw


class CircuitBreaker:
    """Simple closed -> open -> half-open breaker (time-injectable for tests)."""

    def __init__(self, *, failure_threshold: int = 5, reset_seconds: float = 60.0,
                 clock=None):
        self.failure_threshold = failure_threshold
        self.reset_seconds = reset_seconds
        self._clock = clock or time.monotonic
        self.failures = 0
        self.opened_at: float | None = None

    @property
    def state(self) -> str:
        if self.opened_at is None:
            return "closed"
        if self._clock() - self.opened_at >= self.reset_seconds:
            return "half-open"
        return "open"

    def allow(self) -> bool:
        return self.state in ("closed", "half-open")

    def record_success(self) -> None:
        self.failures = 0
        self.opened_at = None

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.failure_threshold:
            self.opened_at = self._clock()
