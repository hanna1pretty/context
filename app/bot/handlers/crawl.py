""" /crawl <url> -- page limit enforced server-side by plan (see workers)."""
from __future__ import annotations
from .._compat import get_router
from ...security.validators import validate_url_no_dns
from ._common import accept
router = get_router()
try:
    from aiogram.filters import Command as _C
    _CMD = _C("crawl")
except Exception:
    _CMD = None
@router.message(_CMD)
async def cmd_crawl(message):
    parts = (message.text or "").split(None, 1)
    if len(parts) < 2:
        await message.answer("Gunakan: /crawl <url>"); return
    try:
        validate_url_no_dns(parts[1])
    except ValueError as exc:
        await message.answer(f"URL ditolak: {exc}"); return
    await accept(message, "crawl", {"url": parts[1], "max_pages": 20})
