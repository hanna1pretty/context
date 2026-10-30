"""Job queue abstraction.

Production: ARQ over Redis (see WorkerSettings in jobs.py / scheduler.py).
Dev / single-process: an in-memory asyncio queue. Handlers only ever call
enqueue() and never await the work itself, so handlers stay fast.
"""
from __future__ import annotations

import asyncio
import hashlib
import uuid
from collections import deque

MAX_QUEUE = 10000


class InMemoryQueue:
    def __init__(self):
        self._q: deque = deque()
        self._seen_idempotency: set[str] = set()

    def enqueue(self, kind: str, user_id: int, payload: dict,
                *, idempotency_key: str | None = None) -> dict:
        if len(self._q) >= MAX_QUEUE:
            raise RuntimeError("queue is full")
        key = idempotency_key or hashlib.sha256(
            f"{user_id}:{kind}:{payload}".encode()).hexdigest()[:32]
        if key in self._seen_idempotency:
            return {"job_id": f"dup-{key[:12]}", "duplicate": True}
        self._seen_idempotency.add(key)
        job_id = uuid.uuid4().hex[:12]
        job = {"job_id": job_id, "kind": kind, "user_id": user_id,
               "payload": payload, "status": "queued"}
        self._q.append(job)
        return {"job_id": job_id, "duplicate": False}

    def pop(self):
        return self._q.popleft() if self._q else None

    def depth(self) -> int:
        return len(self._q)


QUEUE = InMemoryQueue()


async def enqueue_job(kind: str, user_id: int, payload: dict, **kwargs) -> dict:
    """Async wrapper so handlers stay async even for the in-memory queue."""
    await asyncio.sleep(0)
    return QUEUE.enqueue(kind, user_id, payload, **kwargs)
