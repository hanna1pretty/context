"""Plan / settings / usage callbacks (v1).

Upgrade is checkout/confirmation ONLY: pressing an upgrade button never
charges anything automatically; it opens the plan screen / checkout
confirmation flow handled outside this module.
"""
from __future__ import annotations

from .base import build

PLANS = ("free", "pro", "business")
LANGUAGES = ("id", "en")
OUTPUTS = ("markdown", "html", "json")


def plan_show() -> str:
    return build("plan", "show")


def plan_upgrade(plan: str) -> str:
    if plan not in PLANS:
        raise ValueError(f"unknown plan: {plan!r}")
    return build("plan", "upgrade", plan)


def plan_detail(plan: str) -> str:
    if plan not in PLANS:
        raise ValueError(f"unknown plan: {plan!r}")
    return build("plan", "detail", plan)


def plan_faq() -> str:
    return build("plan", "faq")


def plan_list() -> str:
    return build("plan", "list")


def settings_language() -> str:
    return build("settings", "language")


def settings_timezone() -> str:
    return build("settings", "timezone")


def settings_notifications() -> str:
    return build("settings", "notifications")


def settings_output() -> str:
    return build("settings", "output")


def settings_clear_history() -> str:
    """First step: show the clear-history confirmation screen."""
    return build("settings", "clear_history")


def settings_confirm_clear() -> str:
    """Second step: actually clear history."""
    return build("settings", "confirm_clear")


def settings_delete_data() -> str:
    """First step: show the delete-data confirmation screen."""
    return build("settings", "delete_data")


def settings_confirm_delete() -> str:
    """Second step: actually delete the user's data."""
    return build("settings", "confirm_delete")


def settings_privacy() -> str:
    return build("settings", "privacy")


def settings_set_language(language: str) -> str:
    if language not in LANGUAGES:
        raise ValueError(f"unknown language: {language!r}")
    return build("settings", "set_language", language)


def settings_set_timezone(timezone: str) -> str:
    return build("settings", "set_timezone", timezone)


def settings_set_output(output: str) -> str:
    if output not in OUTPUTS:
        raise ValueError(f"unknown output: {output!r}")
    return build("settings", "set_output", output)


def settings_toggle_notifications() -> str:
    return build("settings", "toggle_notifications")
