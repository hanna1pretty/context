""" /scrape <url> -- async, validate (no DNS) -> enqueue -> ack."""
from __future__ import annotations
from .._compat import get_router
from ...security.validators import validate_url_no_dns
from ._common import accept
router = get_router()
try:
    from aiogram.filters import Command as _C
    _CMD = _C("scrape")
except Exception:
    _CMD = None
@router.message(_CMD)
async def cmd_scrape(message):
    arg = (message.text or "").split(None, 1)[1] if len((message.text or "").split(None, 1)) > 1 else ""
    if not arg:
        await message.answer("Gunakan: /scrape <url>"); return
    try:
        validate_url_no_dns(arg)
    except ValueError as exc:
        await message.answer(f"URL ditolak: {exc}"); return
    await accept(message, "scrape", {"url": arg, "formats": {"markdown": True}})
