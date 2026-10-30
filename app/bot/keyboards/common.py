"""Shared keyboard construction.

aiogram import is guarded so the module is importable without aiogram
installed. Fallback shape: a list of ROWS, each row a list of
``{"text": ..., "callback_data": ...}`` dicts (row-preserving, unlike the
old flat-list fallback in keyboards.py — see DECISIONS.md).
``extract_buttons`` / ``iter_callbacks`` normalise both shapes, so tests
and handlers never depend on which backend built the keyboard.
"""
from __future__ import annotations

from ..callbacks.navigation import nav_back, nav_home

try:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    _HAS = True
except Exception:  # pragma: no cover
    _HAS = False
    InlineKeyboardButton = InlineKeyboardMarkup = None  # type: ignore


def _mk(rows):
    rows = [list(row) for row in rows if row]
    if _HAS:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t, callback_data=c) for t, c in row]
            for row in rows])
    return [[{"text": t, "callback_data": c} for t, c in row] for row in rows]


def back_home_row() -> list[tuple[str, str]]:
    """Every submenu ends with these two buttons (spec section 1)."""
    return [("‹ Kembali", nav_back()), ("Menu Utama", nav_home())]


def with_back_home(rows) -> list:
    return [list(r) for r in rows] + [back_home_row()]


def pagination_row(namespace: str, page: int, total_pages: int) -> list[tuple[str, str]]:
    """``[< Prev] [page / total] [Next >]``.

    Prev is omitted on page 1 and Next on the last page (spec section 21).
    The middle indicator is NOT a dead button: it re-requests the current
    page (a harmless refresh), so every button has a recognised handler.
    """
    if total_pages < 1:
        total_pages = 1
    page = max(1, min(page, total_pages))
    row: list[tuple[str, str]] = []
    if page > 1:
        row.append(("‹ Prev", f"{namespace}:v1:page:{page - 1}"))
    row.append((f"{page} / {total_pages}", f"{namespace}:v1:page:{page}"))
    if page < total_pages:
        row.append(("Next ›", f"{namespace}:v1:page:{page + 1}"))
    return row


def error_keyboard(kind: str, back_screen: str = "home") -> list:
    """Error-state buttons (spec section 20). ``kind`` is one of
    validation / rate_limit / quota / context_error."""
    from ..callbacks.navigation import nav_screen
    back_cb = nav_screen(back_screen)
    if kind == "validation":
        rows = [[("Coba Lagi", nav_back()), ("Kembali", back_cb)]]
    elif kind == "rate_limit":
        from ..callbacks.batches import job_list
        rows = [[("Refresh Status", job_list("active")),
                 ("Job Saya", nav_screen("job_center"))]]
    elif kind == "quota":
        from ..callbacks.account import plan_show
        rows = [[("Lihat Usage", nav_screen("usage")),
                 ("Lihat Paket", plan_show())]]
    elif kind == "context_error":
        rows = [[("Coba Lagi", nav_back()), ("Menu Utama", nav_home())]]
    else:
        rows = [[("Kembali", back_cb), ("Menu Utama", nav_home())]]
    return _mk(rows)


def extract_buttons(markup) -> list[dict]:
    """Normalise any keyboard shape to a flat list of button dicts."""
    if markup is None:
        return []
    rows = getattr(markup, "inline_keyboard", None)
    if rows is None:
        rows = markup
    buttons: list[dict] = []
    for row in rows:
        if isinstance(row, dict):
            buttons.append(row)
            continue
        for btn in row:
            if isinstance(btn, dict):
                buttons.append(btn)
            else:
                buttons.append({"text": getattr(btn, "text", ""),
                                "callback_data": getattr(btn, "callback_data", "")})
    return buttons


def iter_callbacks(markup) -> list[str]:
    return [b["callback_data"] for b in extract_buttons(markup) if b.get("callback_data")]


def button_texts(markup) -> list[str]:
    return [b["text"] for b in extract_buttons(markup)]
