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
        # In-flight only, NOT forever: a key is released when its job
        # is popped for execution. The old code kept every key forever
        # and returned a fake "dup-..." job id for a repeat request,
        # while accept() still told the user "Antrian diterima" — so a
        # second /scrape of the same URL could never produce a result.
        self._inflight: dict[str, str] = {}

    def enqueue(self, kind: str, user_id: int, payload: dict,
                *, idempotency_key: str | None = None) -> dict:
        if len(self._q) >= MAX_QUEUE:
            raise RuntimeError("queue is full")
        key = idempotency_key or hashlib.sha256(
            f"{user_id}:{kind}:{payload}".encode()).hexdigest()[:32]
        if key in self._inflight:
            return {"job_id": self._inflight[key], "duplicate": True}
        job_id = uuid.uuid4().hex[:12]
        self._inflight[key] = job_id
        job = {"job_id": job_id, "kind": kind, "user_id": user_id,
               "payload": payload, "status": "queued",
               "_idempotency_key": key}
        self._q.append(job)
        return {"job_id": job_id, "duplicate": False}

    def pop(self):
        if not self._q:
            return None
        job = self._q.popleft()
        self._inflight.pop(job.get("_idempotency_key"), None)
        return job

    def depth(self) -> int:
        return len(self._q)


QUEUE = InMemoryQueue()


async def enqueue_job(kind: str, user_id: int, payload: dict, **kwargs) -> dict:
    """Async wrapper so handlers stay async even for the in-memory queue."""
    await asyncio.sleep(0)
    return QUEUE.enqueue(kind, user_id, payload, **kwargs)
