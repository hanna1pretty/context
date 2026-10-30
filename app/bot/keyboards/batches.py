"""Batches + Job Center keyboards (spec section 14)."""
from __future__ import annotations

from ..callbacks.batches import (
    batch_cancel, batch_delete, batch_list, batch_new, batch_result,
    batch_retry, batch_status,
    job_cancel, job_delete, job_list, job_refresh, job_result, job_retry,
    job_status,
)
from ..callbacks.navigation import nav_home, nav_screen
from .common import _mk, pagination_row, with_back_home


def job_center_menu():
    return _mk(with_back_home([
        [("Job Aktif", job_list("active")), ("Selesai", job_list("done"))],
        [("Gagal", job_list("failed")), ("Semua Job", job_list("all"))],
        [("Refresh", job_list("active"))],
    ]))


def job_list_keyboard(page: int, total_pages: int, job_ids: list[str]):
    rows: list = []
    for job_id in job_ids:
        rows.append([(f"Job {job_id}", job_status(job_id))])
    rows.append(pagination_row("job", page, total_pages))
    rows.append([("‹ Kembali", nav_screen("job_center")), ("Menu Utama", nav_home())])
    return _mk(rows)


def job_actions(job_id: str):
    """v1 replacement for the old ``job:*`` actions (those callbacks were
    never consumed by any handler). Status/result are the real state —
    never a fabricated progress value."""
    return _mk([
        [("Status", job_status(job_id)), ("Hasil", job_result(job_id))],
        [("Batalkan", job_cancel(job_id)), ("Coba Lagi", job_retry(job_id))],
        [("Hapus", job_delete(job_id)), ("Refresh", job_refresh(job_id))],
    ])


def batches_menu():
    return _mk(with_back_home([
        [("Batch Baru", batch_new()), ("Daftar Batch", batch_list())],
        [("Job Center", nav_screen("job_center"))],
    ]))


def batch_actions(batch_id: str):
    return _mk([
        [("Status", batch_status(batch_id)), ("Hasil", batch_result(batch_id))],
        [("Batalkan", batch_cancel(batch_id)), ("Coba Lagi", batch_retry(batch_id))],
        [("Hapus", batch_delete(batch_id))],
    ])
