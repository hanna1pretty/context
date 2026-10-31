"""Single-process job consumer: the missing link that left every job
at "memproses..." forever.

Handlers enqueue into workers/queue.py InMemoryQueue. Nothing in the
bot process ever popped that queue, and nothing enqueued to ARQ/Redis,
so jobs never ran and never delivered a result. This module closes
that loop for the single-process deployment (the deployment the
docker-compose ``bot`` service actually runs):

  pop job -> send a clear progress message -> run_job_with_timeout
  (key resolved from the bot process's admin KEY_STORE, env fallback)
  -> deliver a clear result message (photo for screenshots, text
  otherwise) or a clear failure message with a next step.

ARQ/Redis remains a future gap: this consumer does NOT make ARQ run
these jobs, and a multi-worker deployment must replace it with a
real ARQ consumer sharing a DB-backed key store (see README).
"""
from __future__ import annotations

import asyncio
import logging

from ..contextdev.errors import ContextDevError
from ..services import admin_key_service as aks
from ..services.notification_service import (
    failure_message,
    progress_message,
    result_message,
)
from ..services.screenshot_delivery import prepare_screenshot_message
from .jobs import run_job_with_timeout
from .queue import QUEUE

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL = 0.5


def _subject(payload: dict) -> str:
    for key in ("url", "query", "question"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _photo_input(data: bytes, mime: str):
    """aiogram BufferedInputFile when aiogram is present, else raw bytes
    (fake bots in tests record whatever they are given)."""
    ext = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}.get(mime, "png")
    try:
        from aiogram.types import BufferedInputFile  # type: ignore

        return BufferedInputFile(data, filename=f"screenshot.{ext}")
    except Exception:
        return data


def _resolve_key(key_store, encryption_key: str | None, env_key: str | None):
    """Sync resolver for run_job: admin-panel stored key, then env."""
    if key_store is None:
        # Import the bot process's store lazily to avoid a hard import
        # cycle when this module is imported standalone in tests.
        try:
            from ..bot.handlers.admin import KEY_STORE as _ADMIN_STORE
        except Exception:
            _ADMIN_STORE = None
        key_store = _ADMIN_STORE
    if key_store is not None:
        return aks.resolve_api_key_from_store(key_store, encryption_key, env_key)
    env = (env_key or "").strip()
    if env:
        return env
    raise aks.ApiKeyMissingError(aks.API_KEY_MISSING_MESSAGE)


async def _send(bot, user_id: int, text: str):
    send = getattr(bot, "send_message", None)
    if not callable(send):
        raise RuntimeError("bot has no send_message")
    result = send(user_id, text, parse_mode="HTML")
    if asyncio.iscoroutine(result):
        await result


async def consume_one(bot, *, queue=None, key_store=None,
                      encryption_key: str | None = None,
                      env_key: str | None = None, client=None,
                      run_job_fn=None) -> dict | None:
    """Run exactly one queued job and deliver its outcome. Returns the
    job dict, or None when the queue was empty. Never raises for a
    job failure: failures are delivered as failure messages."""
    q = queue if queue is not None else QUEUE
    job = q.pop()
    if job is None:
        return None
    job_id = job.get("job_id", "unknown")
    kind = job.get("kind", "unknown")
    user_id = job.get("user_id")
    payload = job.get("payload") or {}
    try:
        await _send(bot, user_id, progress_message(job_id, kind, payload=payload))
    except Exception as exc:  # progress is best-effort; the job still runs
        logger.exception("progress message failed for job %s: %s", job_id, exc)
    ctx: dict = {}
    if client is not None:
        ctx["client"] = client
    else:
        def _resolver(_ks=key_store, _ek=encryption_key, _env=env_key):
            return _resolve_key(_ks, _ek, _env)

        ctx["api_key_resolver"] = _resolver
    runner = run_job_fn or run_job_with_timeout
    try:
        result = await runner(ctx, kind=kind, user_id=user_id, payload=payload)
    except Exception as exc:
        reason = str(exc) or exc.__class__.__name__
        logger.exception("job %s failed: %s", job_id, exc)
        try:
            await _send(bot, user_id, failure_message(
                job_id, kind, reason, payload=payload))
        except Exception:
            logger.exception("failure message failed for job %s", job_id)
        return job
    if isinstance(result, dict) and result.get("status") == "accepted-bookkeeping":
        try:
            await _send(bot, user_id,
                        f"✅ <b>Permintaan dicatat</b>\nJob: <code>{job_id}</code>\n"
                        f"Jenis: {kind}\n"
                        "Jenis ini dicatat sebagai bookkeeping dan tidak "
                        "memanggil Context.dev langsung.")
        except Exception:
            logger.exception("bookkeeping message failed for job %s", job_id)
        return job
    # Screenshot jobs: photo first (caption carries title/URL/credits),
    # then the full result text. Non-photo jobs: result text only.
    try:
        if kind == "scrape" and isinstance(result, dict) and result.get("screenshot_data_url_present"):
            prepared = prepare_screenshot_message(result)
            if prepared["kind"] == "photo":
                send_photo = getattr(bot, "send_photo", None)
                if callable(send_photo):
                    photo = _photo_input(prepared["bytes"], prepared["mime"])
                    sent = send_photo(user_id, photo, caption=prepared["caption"],
                                      parse_mode="HTML")
                    if asyncio.iscoroutine(sent):
                        await sent
                else:
                    await _send(bot, user_id, prepared["caption"])
        await _send(bot, user_id, result_message(job_id, kind, result))
    except Exception:
        logger.exception("result delivery failed for job %s", job_id)
        try:
            await _send(bot, user_id, result_message(job_id, kind, result))
        except Exception:
            logger.exception("result retry also failed for job %s", job_id)
    return job


async def consume_forever(bot, *, queue=None, poll_interval: float = DEFAULT_POLL_INTERVAL,
                          key_store=None, encryption_key: str | None = None,
                          env_key: str | None = None, client=None) -> None:
    """Loop forever: pop, run, deliver. Cancel the task to stop."""
    while True:
        job = await consume_one(bot, queue=queue, key_store=key_store,
                                encryption_key=encryption_key, env_key=env_key,
                                client=client)
        if job is None:
            await asyncio.sleep(poll_interval)
