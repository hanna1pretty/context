""" /batch -- large URL lists / large crawls go through batches."""
from __future__ import annotations
from .._compat import get_router
from ._common import accept
router = get_router()
try:
    from aiogram.filters import Command as _C
    _CMD = _C("batch")
except Exception:
    _CMD = None
@router.message(_CMD)
async def cmd_batch(message):
    parts = (message.text or "").split(None, 1)
    if len(parts) < 2:
        await message.answer("Gunakan: /batch <url1,url2,...>"); return
    urls = [u.strip() for u in parts[1].split(",") if u.strip()]
    await accept(message, "batches", {"urls": urls})
