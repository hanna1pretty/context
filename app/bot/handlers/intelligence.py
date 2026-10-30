""" /brand, /styleguide, /people, /company, /news -- intelligence features.
People search is for lawful use cases only; see SECURITY.md privacy notice.
Handlers only validate + enqueue; entitlement is checked server-side in
workers/jobs.py (never by hiding buttons alone)."""
from __future__ import annotations
from .._compat import get_router
from ._common import accept
router = get_router()
try:
    from aiogram.filters import Command as _C
    _CMDS = {"brand": _C("brand"), "styleguide": _C("styleguide"),
             "people": _C("people"), "company": _C("company"), "news": _C("news")}
except Exception:
    _CMDS = {}

async def _run(message, kind):
    parts = (message.text or "").split(None, 1)
    if len(parts) < 2:
        await message.answer(f"Gunakan: /{kind} <query>"); return
    await accept(message, kind, {"query": parts[1]})

@router.message(_CMDS.get("brand"))
async def cmd_brand(m): await _run(m, "brand")
@router.message(_CMDS.get("styleguide"))
async def cmd_styleguide(m): await _run(m, "styleguide")
@router.message(_CMDS.get("people"))
async def cmd_people(m): await _run(m, "people")
@router.message(_CMDS.get("company"))
async def cmd_company(m): await _run(m, "company")
@router.message(_CMDS.get("news"))
async def cmd_news(m): await _run(m, "news")
