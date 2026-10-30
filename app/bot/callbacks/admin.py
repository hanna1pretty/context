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
