"""Main menu (spec section 5): 2-column layout, short labels, admin
button ONLY when ``is_admin`` is True. Hiding is UX only — every admin
action re-checks ADMIN_TELEGRAM_IDS server-side."""
from __future__ import annotations

from ..callbacks.admin import admin_dashboard
from ..callbacks.navigation import nav_screen
from .common import _mk


def main_menu(is_admin: bool = False):
    rows = [
        [("Scrape URL", nav_screen("scrape")), ("Search Web", nav_screen("search"))],
        [("Crawl Website", nav_screen("crawl")), ("Map URLs", nav_screen("map"))],
        [("Ask / Answers", nav_screen("answers")), ("Parse File", nav_screen("parse"))],
        [("Brand Intel", nav_screen("intelligence")), ("People", nav_screen("people"))],
        [("Company", nav_screen("company")), ("News", nav_screen("news"))],
        [("Batches", nav_screen("batches")), ("Monitors", nav_screen("monitors"))],
        [("Usage & Paket", nav_screen("usage")), ("Pengaturan", nav_screen("settings"))],
    ]
    if is_admin:
        rows.append([("Bantuan", nav_screen("help")), ("Menu Admin", admin_dashboard())])
    else:
        rows.append([("Bantuan", nav_screen("help"))])
    return _mk(rows)


def url_choices(url: str):
    """Bare-URL conversational choices. The URL itself is stored
    server-side against the message/job and is never put in callback
    data (previous ``url:*`` callbacks are replaced by v1 callbacks)."""
    from ..callbacks.answers import answers_start
    from ..callbacks.crawl import crawl_start
    from ..callbacks.map_urls import map_start
    from ..callbacks.scrape import scrape_mode
    return _mk([
        [("Scrape Markdown", scrape_mode("markdown")), ("Scrape HTML", scrape_mode("html"))],
        [("Screenshot", scrape_mode("screenshot")), ("Extract JSON", scrape_mode("json"))],
        [("Crawl", crawl_start()), ("Map", map_start())],
        [("Ask about URL", answers_start())],
    ])
