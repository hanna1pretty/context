"""Crawl keyboards (spec section 8)."""
from __future__ import annotations

from ..callbacks.crawl import crawl_cancel, crawl_confirm, crawl_param, crawl_start
from ..callbacks.navigation import nav_home, nav_screen
from .common import _mk, with_back_home


def crawl_menu():
    return _mk(with_back_home([
        [("Mulai Crawl", crawl_start())],
        [("Atur Jumlah Halaman", crawl_param("pages"))],
        [("Atur Depth", crawl_param("depth")), ("Path Include/Exclude", crawl_param("paths"))],
        [("Subdomain", crawl_param("subdomain")), ("Mode Output", crawl_param("output"))],
    ]))


def crawl_confirm_keyboard():
    return _mk([
        [("Mulai Crawl", crawl_confirm()), ("Ubah Parameter", nav_screen("crawl"))],
        [("Batalkan", crawl_cancel()), ("Menu Utama", nav_home())],
    ])
