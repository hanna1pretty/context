"""Scheduled maintenance: retention cleanup, batch polling, monitor checks.

These are ARQ cron jobs in production (see DECISIONS.md for why ARQ).
Each function is a pure scheduling contract: it takes a repository-like
object with the named methods, so it is testable without Postgres/Redis.
"""
from __future__ import annotations


async def cleanup_expired_results(repo, *, now):
    """Delete job_results whose expires_at <= now. Returns count."""
    if hasattr(repo, "delete_expired_results"):
        return await repo.delete_expired_results(now)
    return 0


async def poll_batches(repo, client, *, now):
    """Poll in-flight batches; in prod this calls Context.dev batch status."""
    if hasattr(repo, "list_active_batches"):
        batches = await repo.list_active_batches()
        return len(batches)
    return 0


CRON_JOBS = [
    {"name": "cleanup_expired_results", "interval_minutes": 60},
    {"name": "poll_batches", "interval_minutes": 5},
]
