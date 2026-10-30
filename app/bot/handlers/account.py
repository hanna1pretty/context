""" /usage, /plan -- read-only account views; data comes from DB in prod.
This handler acks with a summary placeholder only when no DB is wired;
production main.py wires the real repository-backed version."""
from __future__ import annotations
from .._compat import get_router
router = get_router()
try:
    from aiogram.filters import Command as _C
    _U = _C("usage"); _P = _C("plan")
except Exception:
    _U = _P = None
@router.message(_U)
async def cmd_usage(message):
    await message.answer("Usage: lihat kredit & limit harian di dashboard admin API "
                         "(/api/admin/usage) atau setelah job pertama tercatat. "
                         "Limit Free default: 10/hari (lihat .env.example).")
@router.message(_P)
async def cmd_plan(message):
    await message.answer("Paket: Free (dasar), Pro (limit lebih tinggi, crawl/parse/export, "
                         "monitor terbatas), Business (tertinggi, monitor lebih banyak). "
                         "Billing bot terpisah dari kredit Context.dev.")
