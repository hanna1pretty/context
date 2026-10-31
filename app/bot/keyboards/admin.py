"""Admin keyboards.

Deliberate backward-compat deviation: the legacy pre-v1 callbacks
(``admin:set_api_key``, ``admin:api_key_status``, ``admin:delete_api_key``,
``admin:cancel_api_key``) are RETAINED and reachable from this menu,
because handlers/admin.py is wired to them. All NEW admin buttons use
v1 callbacks. Button hiding alone never authorises: every admin action
re-checks ADMIN_TELEGRAM_IDS in the service layer.
"""
from __future__ import annotations

from ..callbacks.admin import (
    admin_banner_delete,
    admin_banner_set,
    admin_dashboard,
    admin_health,
    admin_stats,
    admin_welcome_reset,
    admin_welcome_set,
    admin_welcome_show,
)
from ..callbacks.navigation import nav_home
from .common import _mk


def admin_menu():
    return _mk([
        [("Set Context API Key", "admin:set_api_key")],
        [("Lihat Status API Key", "admin:api_key_status")],
        [("Hapus API Key", "admin:delete_api_key")],
        [("Atur Sambutan", admin_welcome_set()), ("Atur Banner", admin_banner_set())],
        [("Lihat Sambutan", admin_welcome_show()), ("Hapus Banner", admin_banner_delete())],
        [("Reset Sambutan", admin_welcome_reset())],
        [("Dashboard", admin_dashboard()), ("Health", admin_health())],
        [("Statistik", admin_stats()), ("Menu Utama", nav_home())],
    ])


def admin_cancel_keyboard():
    return _mk([
        [("Batal", "admin:cancel_api_key")],
    ])


def admin_welcome_cancel_keyboard():
    from ..callbacks.admin import admin_welcome_cancel

    return _mk([
        [("Batal", admin_welcome_cancel())],
    ])


def admin_dashboard_keyboard():
    return _mk([
        [("Health", admin_health()), ("Statistik", admin_stats())],
        [("Set Context API Key", "admin:set_api_key")],
        [("Lihat Status API Key", "admin:api_key_status")],
        [("Atur Sambutan", admin_welcome_set()), ("Atur Banner", admin_banner_set())],
        [("Menu Utama", nav_home())],
    ])
