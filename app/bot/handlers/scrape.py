""" /scrape <url> -- direct run with live progress, NOT a blind queue.

Why this changed: the old path enqueued into InMemoryQueue and
answered "Antrian diterima", but a repeat of the same URL returned a
fake "dup-..." job id (the queue kept every idempotency key forever)
and no job was ever created — so the user sat at "mengantre" forever
with nothing actually running. The queue bug is also fixed
(workers/queue.py now releases a key when its job is popped), but
/scrape no longer needs the queue at all for the common case: it runs
in the handler, edits one progress message through visible stages
(Telegram has no spinner, so staged ⏳ text edits ARE the spinner),
then delivers the result as a new message. No "mengantre" step.
"""
from __future__ import annotations

import asyncio
import os

from .._compat import get_router
from ..callbacks.scrape import scrape_mode_to_formats
from ...security.validators import escape_html, validate_url_no_dns
from ...services import admin_key_service as aks
from ...services.notification_service import result_message
from ...workers.jobs import run_job_with_timeout
from ._common import send_html

router = get_router()
try:
    from aiogram.filters import Command as _C
    _CMD = _C("scrape")
except Exception:
    _CMD = None


def scrape_job_payload(url: str, mode: str = "markdown") -> dict:
    """Build the worker payload for a scrape mode.

    This is the single place that translates a user-visible mode into
    Context.dev `formats` (see contextdev/formats.py). The menu
    confirm flow (handlers/feature_callbacks.py) currently enqueues
    only {"callback": data} and therefore cannot yet recover the
    URL/mode from FSM state — that exact gap is documented in
    README/DECISIONS. Once FSM state is passed into the confirm
    handler, it should call this helper with the stored URL/mode
    instead of enqueuing the bare callback.
    """
    return {"url": url, "formats": scrape_mode_to_formats(mode)}


def _api_key_resolver():
    """Admin-panel stored key, then env — same order as the consumer."""
    try:
        from .admin import KEY_STORE
    except Exception:
        KEY_STORE = None
    if KEY_STORE is not None:
        return aks.resolve_api_key_from_store(
            KEY_STORE,
            os.environ.get("SETTINGS_ENCRYPTION_KEY") or None,
            os.environ.get("CONTEXT_DEV_API_KEY") or None,
        )
    env = (os.environ.get("CONTEXT_DEV_API_KEY") or "").strip()
    if env:
        return env
    raise aks.ApiKeyMissingError(aks.API_KEY_MISSING_MESSAGE)


async def _edit_progress(progress_msg, text: str):
    """Edit the progress message; return True if the edit landed."""
    edit = getattr(progress_msg, "edit_text", None)
    if not callable(edit):
        return False
    try:
        result = edit(text, parse_mode="HTML")
        if asyncio.iscoroutine(result):
            await result
        return True
    except Exception:
        return False


@router.message(_CMD)
async def cmd_scrape(message):
    arg = (message.text or "").split(None, 1)[1] if len((message.text or "").split(None, 1)) > 1 else ""
    if not arg:
        await message.answer("Gunakan: /scrape <url>")
        return
    try:
        validate_url_no_dns(arg)
    except ValueError as exc:
        await message.answer(f"URL ditolak: {exc}")
        return
    user_id = message.from_user.id
    payload = scrape_job_payload(arg, "markdown")
    # Stage 1 — visible immediately, so the user never stares at a
    # static "mengantre" acknowledgement while work happens.
    progress_msg = await message.answer(
        "⏳ <b>Sedang men-scrape…</b>\n"
        f"Target: {escape_html(arg)}\n"
        "Tahap 1/3: Menghubungi Context.dev…",
        parse_mode="HTML",
    )
    # Stage 2 — the "running text": the same message is edited so the
    # user sees movement while the Context.dev call is in flight.
    await _edit_progress(
        progress_msg,
        "⏳ <b>Sedang men-scrape…</b>\n"
        f"Target: {escape_html(arg)}\n"
        "Tahap 2/3: Membaca halaman, tunggu sebentar…",
    )
    try:
        result = await run_job_with_timeout(
            {"api_key_resolver": _api_key_resolver},
            kind="scrape", user_id=user_id, payload=payload,
        )
    except Exception as exc:
        reason = str(exc) or exc.__class__.__name__
        await _edit_progress(
            progress_msg,
            "❌ <b>Scrape gagal</b>\n"
            f"Target: {escape_html(arg)}\n"
            f"Alasan: {escape_html(reason[:500])}\n"
            "Langkah berikutnya: coba lagi, atau buka Bantuan untuk contoh perintah.",
        )
        return
    # Stage 3 — mark the progress message done, then deliver the real
    # result as its own message (never leave the user at "mengantre").
    await _edit_progress(
        progress_msg,
        "✅ <b>Scrape selesai</b>\n"
        f"Target: {escape_html(arg)}\n"
        "Hasilnya ada di pesan berikutnya.",
    )
    await send_html(message, result_message("langsung", "scrape", result))
