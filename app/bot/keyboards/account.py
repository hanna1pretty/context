"""Usage / plan / settings / help keyboards (spec sections 16-18).

Upgrade buttons are checkout/confirmation ONLY — pressing one never
charges anything automatically. Destructive settings actions are
two-step: first tap opens a confirmation screen, second tap confirms.
"""
from __future__ import annotations

from ..callbacks.account import (
    plan_detail, plan_faq, plan_show, plan_upgrade,
    settings_clear_history, settings_confirm_clear, settings_confirm_delete,
    settings_delete_data, settings_language, settings_notifications,
    settings_output, settings_privacy, settings_set_language,
    settings_timezone,
)
from ..callbacks.batches import job_list
from ..callbacks.navigation import nav_home, nav_screen
from .common import _mk, with_back_home


def usage_keyboard():
    return _mk(with_back_home([
        [("Detail Usage", nav_screen("usage")), ("Riwayat Job", job_list("all"))],
        [("Free", plan_detail("free")), ("Pro", plan_detail("pro"))],
        [("Business", plan_detail("business")), ("FAQ Paket", plan_faq())],
        [("Upgrade", plan_show())],
    ]))


def plan_keyboard():
    return _mk(with_back_home([
        [("Free", plan_detail("free")), ("Pro", plan_detail("pro"))],
        [("Business", plan_detail("business")), ("FAQ Paket", plan_faq())],
        [("Upgrade ke Pro", plan_upgrade("pro")),
         ("Upgrade ke Business", plan_upgrade("business"))],
    ]))


def locked_feature_keyboard(feature: str = ""):
    """A locked feature's button routes to the plan screen (never dead)."""
    label = f"🔒 Fitur Pro — Lihat Paket" if not feature else f"🔒 {feature} — Lihat Paket"
    return _mk([
        [(label, plan_show())],
        [("‹ Kembali", nav_screen("usage")), ("Menu Utama", nav_home())],
    ])


def settings_menu():
    return _mk(with_back_home([
        [("Bahasa", settings_language()), ("Timezone", settings_timezone())],
        [("Notifikasi", settings_notifications()), ("Default Output", settings_output())],
        [("Clear History", settings_clear_history()), ("Hapus Data Saya", settings_delete_data())],
        [("Privacy", settings_privacy())],
    ]))


def settings_language_keyboard():
    return _mk(with_back_home([
        [("Indonesia", settings_set_language("id")), ("English", settings_set_language("en"))],
    ]))


def settings_clear_confirm_keyboard():
    return _mk([
        [("Ya, Hapus History", settings_confirm_clear()), ("Tidak", nav_screen("settings"))],
    ])


def settings_delete_confirm_keyboard():
    return _mk([
        [("Ya, Hapus Data Saya", settings_confirm_delete()), ("Tidak", nav_screen("settings"))],
    ])


def help_menu():
    return _mk(with_back_home([
        [("Semua Command", nav_screen("help_commands"))],
        [("Contoh Penggunaan", nav_screen("help_examples")), ("Status Sistem", nav_screen("help_status"))],
        [("Privacy & Data", nav_screen("help_privacy")), ("Hubungi Admin", nav_screen("help"))],
    ]))
