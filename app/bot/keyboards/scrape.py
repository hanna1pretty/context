"""Scrape keyboards (spec section 6)."""
from __future__ import annotations

from ..callbacks.navigation import nav_screen
from ..callbacks.scrape import (
    scrape_browser_actions, scrape_cancel, scrape_confirm, scrape_help,
    scrape_mode, scrape_options,
)
from .common import _mk, with_back_home


def scrape_menu():
    return _mk(with_back_home([
        [("Markdown", scrape_mode("markdown")), ("HTML", scrape_mode("html"))],
        [("Screenshot", scrape_mode("screenshot")), ("Extract JSON", scrape_mode("json"))],
        [("Highlights", scrape_mode("highlights")), ("Fresh Fetch", scrape_mode("fresh"))],
        [("Browser Actions", scrape_browser_actions()), ("Bantuan Scrape", scrape_help())],
    ]))


def scrape_confirm_keyboard():
    """Confirmation card actions. State (URL/mode/options) lives in FSM
    server-side; nothing about the URL is in the callback data."""
    return _mk([
        [("Mulai", scrape_confirm()), ("Ubah Mode", nav_screen("scrape"))],
        [("Atur Opsi", scrape_options()), ("Batalkan", scrape_cancel())],
    ])


def scrape_fresh_warning_keyboard():
    """Fresh Fetch cost/latency warning: confirm anyway, or pick a mode."""
    return _mk([
        [("Tetap Fresh Fetch", scrape_confirm()), ("Ubah Mode", nav_screen("scrape"))],
        [("Batalkan", scrape_cancel())],
    ])
