"""Per-user rate limiting + concurrency tracking. Pure stdlib, in-memory.

Production wiring (Redis-backed) lives behind the same interface in
app/workers/queue.py notes; this in-memory version is what tests use and
what a single-process dev run uses. It never blocks the event loop.
"""
from __future__ import annotations

import time
from collections import deque


class SlidingWindowLimiter:
    """Allow at most `max_calls` per `window_seconds` per key."""

    def __init__(self, max_calls: int, window_seconds: float,
                 *, clock=None):
        self.max_calls = max_calls
        self.window = window_seconds
        self._clock = clock or time.monotonic
        self._hits: dict[str, deque] = {}

    def allow(self, key: str) -> bool:
        now = self._clock()
        q = self._hits.setdefault(key, deque())
        while q and q[0] <= now - self.window:
            q.popleft()
        if len(q) >= self.max_calls:
            return False
        q.append(now)
        return True

    def remaining(self, key: str) -> int:
        now = self._clock()
        q = self._hits.get(key, deque())
        live = [t for t in q if t > now - self.window]
        return max(0, self.max_calls - len(live))


class ConcurrencyTracker:
    """Count in-flight jobs per user; reject above the per-user cap."""

    def __init__(self, max_per_user: int):
        self.max_per_user = max_per_user
        self._counts: dict[int, int] = {}

    def acquire(self, user_id: int) -> bool:
        if self._counts.get(user_id, 0) >= self.max_per_user:
            return False
        self._counts[user_id] = self._counts.get(user_id, 0) + 1
        return True

    def release(self, user_id: int) -> None:
        self._counts[user_id] = max(0, self._counts.get(user_id, 0) - 1)

    def in_flight(self, user_id: int) -> int:
        return self._counts.get(user_id, 0)
