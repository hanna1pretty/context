"""Inline keyboards. aiogram import is guarded so the module is importable
without aiogram installed (falls back to plain dict buttons for tests/docs)."""
from __future__ import annotations

try:
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    _HAS = True
except Exception:  # pragma: no cover
    _HAS = False
    InlineKeyboardButton = InlineKeyboardMarkup = None  # type: ignore


def _mk(rows):
    if _HAS:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t, callback_data=c) for t, c in row] for row in rows])
    return [{"text": t, "callback_data": c} for row in rows for t, c in row]


def main_menu():
    return _mk([
        [("Scrape URL", "menu:scrape"), ("Search Web", "menu:search")],
        [("Crawl Website", "menu:crawl"), ("Map URLs", "menu:map")],
        [("Ask / Answers", "menu:ask"), ("Parse File", "menu:parse")],
        [("Company Intelligence", "menu:company"), ("People Search", "menu:people")],
        [("News Search", "menu:news"), ("Batches", "menu:batch")],
        [("Monitors", "menu:monitor"), ("Paket & Usage", "menu:usage")],
        [("Bantuan", "menu:help"), ("Pengaturan", "menu:settings")],
    ])


def url_choices(url: str):
    # Callback data carries only an action; the URL itself is stored server-side
    # against the message/job, never trusted blindly from callback data.
    return _mk([
        [("Scrape Markdown", "url:scrape_md"), ("Scrape HTML", "url:scrape_html")],
        [("Screenshot", "url:screenshot"), ("Extract JSON", "url:extract")],
        [("Crawl", "url:crawl"), ("Map", "url:map")],
        [("Ask about URL", "url:ask")],
    ])


def admin_menu():
    """Admin panel only. Buttons alone never authorise: every action
    re-checks ADMIN_TELEGRAM_IDS in the service layer."""
    return _mk([
        [("Set Context API Key", "admin:set_api_key")],
        [("Lihat Status API Key", "admin:api_key_status")],
        [("Hapus API Key", "admin:delete_api_key")],
    ])


def admin_cancel_keyboard():
    return _mk([
        [("Batal", "admin:cancel_api_key")],
    ])


def job_actions(job_id: str):
    return _mk([
        [("Lihat sumber", f"job:sources:{job_id}"), ("Export", f"job:export:{job_id}")],
        [("Refresh", f"job:refresh:{job_id}"), ("Coba lagi", f"job:retry:{job_id}")],
        [("Hapus hasil", f"job:delete:{job_id}")],
    ])
