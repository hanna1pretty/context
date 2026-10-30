"""Assemble all handler routers."""
from __future__ import annotations

from .handlers import (
    account, admin, answers, batches, crawl, feature_callbacks,
    intelligence, map, monitors, navigation, parse, scrape, search, start,
)
from ._compat import get_router

router = get_router()
# Admin FIRST: its awaiting-input / awaiting-cancel filters must be
# evaluated before start.py's bare-text catch-all, or a key typed by an
# awaiting admin would be swallowed as a search query.
# Navigation + feature callbacks LAST: their filters are prefix-based,
# so legacy admin callbacks (admin:set_api_key, ...) must reach
# handlers/admin.py first, and nav:* must not shadow feature handlers.
for mod in (admin, start, scrape, search, crawl, map, answers, parse, intelligence,
            batches, monitors, account, navigation, feature_callbacks):
    try:
        router.include_router(mod.router)
    except Exception:
        pass
