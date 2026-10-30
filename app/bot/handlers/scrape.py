""" /scrape <url> -- async, validate (no DNS) -> enqueue -> ack."""
from __future__ import annotations
from .._compat import get_router
from ..callbacks.scrape import scrape_mode_to_formats
from ...security.validators import validate_url_no_dns
from ._common import accept
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


@router.message(_CMD)
async def cmd_scrape(message):
    arg = (message.text or "").split(None, 1)[1] if len((message.text or "").split(None, 1)) > 1 else ""
    if not arg:
        await message.answer("Gunakan: /scrape <url>"); return
    try:
        validate_url_no_dns(arg)
    except ValueError as exc:
        await message.answer(f"URL ditolak: {exc}"); return
    await accept(message, "scrape", scrape_job_payload(arg, "markdown"))
