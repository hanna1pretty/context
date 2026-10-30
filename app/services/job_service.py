"""Job lifecycle + ownership. Pure stdlib; persistence via repositories in prod."""
from __future__ import annotations

from dataclasses import dataclass, field

CANCELLABLE = {"queued", "running"}


@dataclass
class Job:
    id: str
    user_id: int
    kind: str
    status: str = "queued"
    context_job_id: str | None = None
    error_code: str | None = None


def owns(job: Job, user_id: int) -> bool:
    return job.user_id == user_id


def can_cancel(job: Job, user_id: int, *, admin: bool = False) -> bool:
    if job.status not in CANCELLABLE:
        return False
    return admin or owns(job, user_id)


def can_view(job: Job, user_id: int, *, admin: bool = False) -> bool:
    return admin or owns(job, user_id)
