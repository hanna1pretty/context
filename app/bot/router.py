"""Assemble all handler routers."""
from __future__ import annotations

from .handlers import account, admin, answers, batches, crawl, intelligence, map, monitors, parse, scrape, search, start
from ._compat import get_router

router = get_router()
# Admin FIRST: its awaiting-input / awaiting-cancel filters must be
# evaluated before start.py's bare-text catch-all, or a key typed by an
# awaiting admin would be swallowed as a search query.
for mod in (admin, start, scrape, search, crawl, map, answers, parse, intelligence,
            batches, monitors, account):
    try:
        router.include_router(mod.router)
    except Exception:
        pass
