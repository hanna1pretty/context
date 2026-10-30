"""Search keyboards (spec section 7). Results use INDEX callbacks."""
from __future__ import annotations

from ..callbacks.navigation import nav_home, nav_screen
from ..callbacks.search import (
    news_filter, news_open, news_read, news_save, news_search,
    search_export, search_filter, search_open, search_read,
    search_save, search_start,
)
from .common import _mk, pagination_row, with_back_home


def search_menu():
    return _mk(with_back_home([
        [("Mulai Pencarian", search_start())],
        [("Filter Domain", search_filter("domain")), ("Filter Waktu", search_filter("time"))],
        [("Bahasa", search_filter("language")), ("Lokasi", search_filter("location"))],
        [("Jumlah Hasil", search_filter("count")), ("Content Result", search_filter("content"))],
    ]))


def search_results_keyboard(page: int, total_pages: int, result_count: int):
    """Per-result [N Buka] [N Baca] pairs, then pagination, then actions.

    Indexes are validated server-side against the requesting user's
    stored result list; a forged index yields a safe 'not found' error.
    """
    rows: list = []
    for idx in range(1, max(0, result_count) + 1):
        rows.append([(f"{idx} Buka", search_open(idx)), (f"{idx} Baca", search_read(idx))])
    rows.append(pagination_row("search", page, total_pages))
    rows.append([("Simpan", search_save()), ("Export", search_export())])
    rows.append([("‹ Kembali", nav_screen("search")), ("Menu Utama", nav_home())])
    return _mk(rows)


def news_menu():
    """News submenu (spec section 13)."""
    return _mk(with_back_home([
        [("Search News", news_search())],
        [("Company News", news_search()), ("Filter Tanggal", news_filter("date"))],
        [("Filter Domain", news_filter("domain")), ("Next Page", news_filter("page"))],
        [("Simpan Query", news_save())],
    ]))


def news_results_keyboard(page: int, total_pages: int, result_count: int):
    rows: list = []
    for idx in range(1, max(0, result_count) + 1):
        rows.append([(f"{idx} Buka", news_open(idx)), (f"{idx} Baca", news_read(idx))])
    rows.append(pagination_row("news", page, total_pages))
    rows.append([("Simpan", news_save())])
    rows.append([("‹ Kembali", nav_screen("news")), ("Menu Utama", nav_home())])
    return _mk(rows)


def search_filter_keyboard():
    return _mk(with_back_home([
        [("Filter Domain", search_filter("domain")), ("Filter Waktu", search_filter("time"))],
        [("Bahasa", search_filter("language")), ("Lokasi", search_filter("location"))],
        [("Jumlah Hasil", search_filter("count")), ("Content Result", search_filter("content"))],
        [("Mulai Pencarian", search_start())],
    ]))
