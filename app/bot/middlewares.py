"""aiogram middlewares: logging context + per-user rate limiting.

Rate limiting here is the in-memory limiter (single process). Production
multi-worker deployments should swap it for the Redis limiter behind the
same allow() interface; the interface is intentionally tiny.
"""
from __future__ import annotations

import uuid

from ..security.rate_limit import ConcurrencyTracker, SlidingWindowLimiter

limiter = SlidingWindowLimiter(max_calls=30, window_seconds=60.0)
concurrency = ConcurrencyTracker(max_per_user=2)

try:
    from aiogram import BaseMiddleware

    class LoggingMiddleware(BaseMiddleware):
        async def __call__(self, handler, event, data):
            data["trace_id"] = str(uuid.uuid4())
            return await handler(event, data)

    class RateLimitMiddleware(BaseMiddleware):
        async def __call__(self, handler, event, data):
            user = getattr(event, "from_user", None)
            if user is not None and not limiter.allow(str(user.id)):
                await event.answer("Terlalu banyak permintaan, coba lagi sebentar.")
                return None
            return await handler(event, data)
except Exception:  # pragma: no cover
    class LoggingMiddleware:  # type: ignore
        pass

    class RateLimitMiddleware:  # type: ignore
        pass
