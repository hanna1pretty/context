"""Shared handler helper: validate -> enqueue -> acknowledge immediately.
No Context.dev call, no blocking call, no time.sleep here.

send_html() is the single place that attaches parse_mode="HTML" to a
message answer. Handlers that send "<b>"/"<code>" text MUST use it;
sending the same text without parse_mode is exactly how the live bot
showed literal "<b>...</b>" tags. Plain-text messages (no HTML tags)
may still use message.answer() directly.
"""
from __future__ import annotations

from ...services.notification_service import accepted_message
from ...workers.queue import enqueue_job


async def send_html(message, text: str, reply_markup=None):
    """Answer with Telegram HTML parsing. Fake-compatible (fakes in
    tests accept parse_mode as a keyword argument)."""
    return await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")


async def accept(message, kind: str, payload: dict) -> str:
    """Enqueue and acknowledge. Returns the job_id.

    The acknowledgement now says explicitly that a progress message
    and then a result message will follow (see workers/consumer.py);
    it no longer leaves the user at a bare "memproses..." state.
    """
    result = await enqueue_job(kind, message.from_user.id, payload)
    await send_html(message, accepted_message(result["job_id"], kind, payload=payload))
    return result["job_id"]
