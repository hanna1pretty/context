"""Admin v1 callbacks.

These are NEW admin buttons. The pre-v1 legacy callbacks
(``admin:set_api_key`` etc.) remain in callbacks/base.py LEGACY_CALLBACKS
and in handlers/admin.py; every admin action re-checks ADMIN_TELEGRAM_IDS
in the service layer, never by button hiding alone.
"""
from __future__ import annotations

from .base import build


def admin_dashboard() -> str:
    return build("admin", "dashboard")


def admin_health() -> str:
    return build("admin", "health")


def admin_stats() -> str:
    return build("admin", "stats")


def admin_welcome_set() -> str:
    return build("admin", "welcome_set")


def admin_welcome_show() -> str:
    return build("admin", "welcome_show")


def admin_welcome_reset() -> str:
    return build("admin", "welcome_reset")


def admin_welcome_cancel() -> str:
    return build("admin", "welcome_cancel")


def admin_banner_set() -> str:
    return build("admin", "banner_set")


def admin_banner_delete() -> str:
    return build("admin", "banner_delete")
