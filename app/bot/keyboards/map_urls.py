"""Map keyboards (spec section 9). Export gated by entitlement: when
``export_allowed`` is False the export buttons become a locked button
that routes to the plan screen instead of a dead button."""
from __future__ import annotations

from ..callbacks.account import plan_show
from ..callbacks.map_urls import map_export, map_filter, map_start
from .common import _mk, pagination_row, with_back_home


def map_menu(export_allowed: bool = False):
    export_row = ([("Export JSON", map_export("json")), ("Export CSV", map_export("csv"))]
                  if export_allowed
                  else [("🔒 Export — Lihat Paket", plan_show())])
    return _mk(with_back_home([
        [("Map Domain", map_start())],
        [("Filter Path", map_filter("path")), ("Filter Subdomain", map_filter("subdomain"))],
        [("Limit URL", map_filter("limit")), ("Filter Topic", map_filter("topic"))],
        export_row,
    ]))


def map_results_keyboard(page: int, total_pages: int, export_allowed: bool = False):
    export_row = ([("Export JSON", map_export("json")), ("Export CSV", map_export("csv"))]
                  if export_allowed
                  else [("🔒 Export — Lihat Paket", plan_show())])
    return _mk(with_back_home([
        pagination_row("map", page, total_pages),
        export_row,
    ]))
