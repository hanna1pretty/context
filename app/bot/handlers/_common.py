"""Shared handler helper: validate -> enqueue -> acknowledge immediately.
No Context.dev call, no blocking call, no time.sleep here."""
from __future__ import annotations

from ...services.notification_service import accepted_message
from ...workers.queue import enqueue_job


async def accept(message, kind: str, payload: dict) -> str:
    """Enqueue and acknowledge. Returns the job_id."""
    result = await enqueue_job(kind, message.from_user.id, payload)
    await message.answer(accepted_message(result["job_id"], kind))
    return result["job_id"]
