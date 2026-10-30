""" /map <domain-or-url>."""
from __future__ import annotations
from .._compat import get_router
from ._common import accept
router = get_router()
try:
    from aiogram.filters import Command as _C
    _CMD = _C("map")
except Exception:
    _CMD = None
@router.message(_CMD)
async def cmd_map(message):
    parts = (message.text or "").split(None, 1)
    if len(parts) < 2:
        await message.answer("Gunakan: /map <domain-atau-url>"); return
    await accept(message, "map", {"url": parts[1]})
