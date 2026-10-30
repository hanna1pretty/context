"""Batch + Job Center callbacks (v1). Only short server-side IDs."""
from __future__ import annotations

from .base import build

JOB_LIST_VIEWS = ("active", "done", "failed", "all")


def job_list(view: str) -> str:
    if view not in JOB_LIST_VIEWS:
        raise ValueError(f"unknown job list view: {view!r}")
    return build("job", "list", view)


def job_status(job_id: str) -> str:
    return build("job", "status", job_id)


def job_result(job_id: str) -> str:
    return build("job", "result", job_id)


def job_cancel(job_id: str) -> str:
    return build("job", "cancel", job_id)


def job_retry(job_id: str) -> str:
    return build("job", "retry", job_id)


def job_delete(job_id: str) -> str:
    return build("job", "delete", job_id)


def job_refresh(job_id: str) -> str:
    return build("job", "refresh", job_id)


def job_sources(job_id: str) -> str:
    return build("job", "sources", job_id)


def job_export(job_id: str) -> str:
    return build("job", "export", job_id)


def batch_new() -> str:
    return build("batch", "new")


def batch_list() -> str:
    return build("batch", "list")


def batch_status(batch_id: str) -> str:
    return build("batch", "status", batch_id)


def batch_result(batch_id: str) -> str:
    return build("batch", "result", batch_id)


def batch_cancel(batch_id: str) -> str:
    return build("batch", "cancel", batch_id)


def batch_retry(batch_id: str) -> str:
    return build("batch", "retry", batch_id)


def batch_delete(batch_id: str) -> str:
    return build("batch", "delete", batch_id)
