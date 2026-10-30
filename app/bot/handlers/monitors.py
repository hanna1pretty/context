""" /monitor -- create/list/pause/resume/delete handled by worker + ownership
check in services/job_service.py style checks (see workers/jobs.py)."""
from __future__ import annotations
from .._compat import get_router
from ._common import accept
router = get_router()
try:
    from aiogram.filters import Command as _C
    _CMD = _C("monitor")
except Exception:
    _CMD = None
@router.message(_CMD)
async def cmd_monitor(message):
    parts = (message.text or "").split(None, 1)
    if len(parts) < 2:
        await message.answer("Gunakan: /monitor <url>  |  /monitor list"); return
    if parts[1].strip() == "list":
        await accept(message, "monitors_list", {}); return
    await accept(message, "monitors", {"url": parts[1]})
