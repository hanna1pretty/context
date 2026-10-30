"""Notification message builders (transport injected by bot/workers). Pure stdlib."""
from __future__ import annotations

from ..security.validators import escape_html


def accepted_message(job_id: str, kind: str) -> str:
    return (f"Permintaan diterima ✅\nJob: <code>{escape_html(job_id)}</code>\n"
            f"Jenis: {escape_html(kind)}\nStatus: memproses…")


def done_message(job_id: str) -> str:
    return f"Job <code>{escape_html(job_id)}</code> selesai ✅"


def failed_message(job_id: str, safe_error: str) -> str:
    return (f"Job <code>{escape_html(job_id)}</code> gagal ❌\n"
            f"{escape_html(safe_error)}\nSilakan coba lagi atau /help.")
