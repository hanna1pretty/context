""" /parse -- file handling: size/MIME checked in worker; handler only acks.
Telegram file download happens in the worker, never in the handler loop
beyond the enqueue (aiogram file fetch is awaited in workers/jobs.py)."""
from __future__ import annotations
from .._compat import get_router
from ._common import accept
router = get_router()
try:
    from aiogram.filters import Command as _C
    _CMD = _C("parse")
except Exception:
    _CMD = None
@router.message(_CMD)
async def cmd_parse(message):
    parts = (message.text or "").split(None, 1)
    payload = {"url": parts[1]} if len(parts) > 1 else {}
    await accept(message, "parse", payload)
