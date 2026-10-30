"""Health endpoints: /health/live (process up) and /health/ready (deps)."""
from __future__ import annotations

from ._compat import get_router

router = get_router()


@router.get("/health/live")
async def live():
    return {"status": "ok"}


@router.get("/health/ready")
async def ready():
    # Real readiness checks DB/Redis/Context.dev ping in main.py wiring;
    # this standalone router reports the process-level contract.
    return {"status": "ok", "checks": {"db": "unknown", "redis": "unknown",
                                        "contextdev": "unknown"}}
