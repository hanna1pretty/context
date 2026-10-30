""" /search <query>."""
from __future__ import annotations
from .._compat import get_router
from ._common import accept
router = get_router()
try:
    from aiogram.filters import Command as _C
    _CMD = _C("search")
except Exception:
    _CMD = None
@router.message(_CMD)
async def cmd_search(message):
    parts = (message.text or "").split(None, 1)
    if len(parts) < 2:
        await message.answer("Gunakan: /search <query>"); return
    await accept(message, "search", {"query": parts[1]})
