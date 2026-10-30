"""Monitor callbacks (v1). Delete is always two-step (see keyboards)."""
from __future__ import annotations

from .base import build


def monitor_new() -> str:
    return build("monitor", "new")


def monitor_list() -> str:
    return build("monitor", "list")


def monitor_changes() -> str:
    return build("monitor", "changes")


def monitor_pause(monitor_id: str) -> str:
    return build("monitor", "pause", monitor_id)


def monitor_resume(monitor_id: str) -> str:
    return build("monitor", "resume", monitor_id)


def monitor_delete(monitor_id: str) -> str:
    """First step: show the delete-confirmation screen, do NOT delete."""
    return build("monitor", "delete", monitor_id)


def monitor_confirm_delete(monitor_id: str) -> str:
    """Second step: actually delete (after the confirmation screen)."""
    return build("monitor", "confirm_delete", monitor_id)


def monitor_pause_all() -> str:
    return build("monitor", "pause_all")


def monitor_help() -> str:
    return build("monitor", "help")
