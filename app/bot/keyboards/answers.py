"""Ask / Answers keyboards (spec section 10)."""
from __future__ import annotations

from ..callbacks.answers import (
    answers_again, answers_export, answers_filter, answers_save,
    answers_source, answers_start, answers_style,
)
from ..callbacks.navigation import nav_screen
from .common import _mk, with_back_home


def answers_menu():
    return _mk(with_back_home([
        [("Mulai Bertanya", answers_start())],
        [("Jawaban Singkat", answers_style("short")), ("Jawaban Detail", answers_style("detail"))],
        [("Jawaban Terstruktur", answers_style("structured"))],
        [("Batasi Domain", answers_filter("domain")), ("Atur Waktu", answers_filter("time"))],
    ]))


def answers_result_keyboard():
    return _mk(with_back_home([
        [("Lihat Sumber", answers_source()), ("Jawaban Lagi", answers_again())],
        [("Ubah Pertanyaan", answers_start()), ("Export", answers_export())],
        [("Simpan", answers_save())],
    ]))
