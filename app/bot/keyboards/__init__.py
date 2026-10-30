"""Keyboard package (REPLACED-BY-DIRECTORY: former keyboards.py).

Legacy names (main_menu, url_choices, admin_menu,
admin_cancel_keyboard, job_actions) are re-exported here so existing
imports keep working. Notes on deliberate changes vs the old file:
- main_menu() now takes is_admin (default False); the admin button
  appears only for admins.
- url_choices() and job_actions() now use v1 callbacks; the old
  ``url:*`` / ``job:*`` callbacks were never consumed by any handler.
- The aiogram-absent fallback now preserves ROWS (list of row lists)
  instead of flattening buttons, so layout can be tested.
"""
from __future__ import annotations

from .account import (
    help_menu,
    locked_feature_keyboard,
    plan_keyboard,
    settings_clear_confirm_keyboard,
    settings_delete_confirm_keyboard,
    settings_language_keyboard,
    settings_menu,
    usage_keyboard,
)
from .admin import admin_cancel_keyboard, admin_dashboard_keyboard, admin_menu
from .answers import answers_menu, answers_result_keyboard
from .batches import (
    batch_actions,
    batches_menu,
    job_actions,
    job_center_menu,
    job_list_keyboard,
)
from .common import (
    back_home_row,
    button_texts,
    error_keyboard,
    extract_buttons,
    iter_callbacks,
    pagination_row,
    with_back_home,
)
from .crawl import crawl_confirm_keyboard, crawl_menu
from .intelligence import (
    brand_menu,
    company_menu,
    intelligence_menu,
    intelligence_result_keyboard,
    people_menu,
)
from .main_menu import main_menu, url_choices
from .map_urls import map_menu, map_results_keyboard
from .monitors import (
    monitor_actions,
    monitor_delete_confirm_keyboard,
    monitor_list_keyboard,
    monitors_menu,
)
from .parse import parse_menu, parse_result_keyboard
from .scrape import (
    scrape_confirm_keyboard,
    scrape_fresh_warning_keyboard,
    scrape_menu,
)
from .search import (
    news_menu,
    news_results_keyboard,
    search_filter_keyboard,
    search_menu,
    search_results_keyboard,
)

__all__ = [
    "main_menu", "url_choices", "admin_menu", "admin_cancel_keyboard",
    "job_actions", "back_home_row", "button_texts", "error_keyboard",
    "extract_buttons", "iter_callbacks", "pagination_row", "with_back_home",
    "scrape_menu", "scrape_confirm_keyboard", "scrape_fresh_warning_keyboard",
    "search_menu", "search_results_keyboard", "search_filter_keyboard",
    "news_menu", "news_results_keyboard",
    "crawl_menu", "crawl_confirm_keyboard", "map_menu", "map_results_keyboard",
    "answers_menu", "answers_result_keyboard", "parse_menu", "parse_result_keyboard",
    "intelligence_menu", "brand_menu", "people_menu", "company_menu",
    "intelligence_result_keyboard", "job_center_menu", "job_list_keyboard",
    "batches_menu", "batch_actions", "monitors_menu", "monitor_actions",
    "monitor_delete_confirm_keyboard", "monitor_list_keyboard",
    "usage_keyboard", "plan_keyboard", "locked_feature_keyboard",
    "settings_menu", "settings_language_keyboard",
    "settings_clear_confirm_keyboard", "settings_delete_confirm_keyboard",
    "help_menu", "admin_dashboard_keyboard",
]
