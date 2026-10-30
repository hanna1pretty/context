"""Monitor keyboards (spec section 15). Delete is always two-step:
the first tap only opens the confirmation screen."""
from __future__ import annotations

from ..callbacks.monitors import (
    monitor_changes, monitor_confirm_delete, monitor_delete, monitor_help,
    monitor_list, monitor_new, monitor_pause, monitor_pause_all,
    monitor_resume,
)
from ..callbacks.navigation import nav_home, nav_screen
from .common import _mk, pagination_row, with_back_home


def monitors_menu():
    return _mk(with_back_home([
        [("Monitor Baru", monitor_new())],
        [("Monitor Saya", monitor_list()), ("Perubahan Terbaru", monitor_changes())],
        [("Pause Semua", monitor_pause_all()), ("Bantuan Monitor", monitor_help())],
    ]))


def monitor_actions(monitor_id: str):
    return _mk([
        [("Pause", monitor_pause(monitor_id)), ("Resume", monitor_resume(monitor_id))],
        [("Perubahan", monitor_changes()), ("Hapus", monitor_delete(monitor_id))],
        [("‹ Kembali", nav_screen("monitors")), ("Menu Utama", nav_home())],
    ])


def monitor_delete_confirm_keyboard(monitor_id: str):
    return _mk([
        [("Ya, Hapus", monitor_confirm_delete(monitor_id)), ("Tidak", nav_screen("monitor_detail"))],
    ])


def monitor_list_keyboard(page: int, total_pages: int, monitor_ids: list[str]):
    rows: list = []
    for monitor_id in monitor_ids:
        rows.append([(f"Monitor {monitor_id}", monitor_pause(monitor_id)),
                     ("Hapus", monitor_delete(monitor_id))])
    rows.append(pagination_row("monitor", page, total_pages))
    rows.append([("‹ Kembali", nav_screen("monitors")), ("Menu Utama", nav_home())])
    return _mk(rows)
