"""Admin keyboards.

Deliberate backward-compat deviation: the legacy pre-v1 callbacks
(``admin:set_api_key``, ``admin:api_key_status``, ``admin:delete_api_key``,
``admin:cancel_api_key``) are RETAINED and reachable from this menu,
because handlers/admin.py is wired to them. All NEW admin buttons use
v1 callbacks. Button hiding alone never authorises: every admin action
re-checks ADMIN_TELEGRAM_IDS in the service layer.
"""
from __future__ import annotations

from ..callbacks.admin import admin_dashboard, admin_health, admin_stats
from ..callbacks.navigation import nav_home
from .common import _mk


def admin_menu():
    return _mk([
        [("Set Context API Key", "admin:set_api_key")],
        [("Lihat Status API Key", "admin:api_key_status")],
        [("Hapus API Key", "admin:delete_api_key")],
        [("Dashboard", admin_dashboard()), ("Health", admin_health())],
        [("Statistik", admin_stats()), ("Menu Utama", nav_home())],
    ])


def admin_cancel_keyboard():
    return _mk([
        [("Batal", "admin:cancel_api_key")],
    ])


def admin_dashboard_keyboard():
    return _mk([
        [("Health", admin_health()), ("Statistik", admin_stats())],
        [("Set Context API Key", "admin:set_api_key")],
        [("Lihat Status API Key", "admin:api_key_status")],
        [("Menu Utama", nav_home())],
    ])
