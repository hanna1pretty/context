"""Internal admin API. Authorization is checked in the service layer here
(ADMIN check), not just by hiding the route: every handler verifies the
caller header against ADMIN_TELEGRAM_IDS via main.py dependency in prod;
this standalone router shows the check explicitly."""
from __future__ import annotations

import os

from ._compat import get_router

router = get_router()


def is_admin_caller(admin_id_header: str | None) -> bool:
    allowed = {p.strip() for p in os.environ.get("ADMIN_TELEGRAM_IDS", "").split(",") if p.strip()}
    return bool(admin_id_header and admin_id_header.strip() in allowed)


@router.get("/api/admin/stats")
async def stats(request):
    admin_id = request.headers.get("x-admin-telegram-id") if hasattr(request, "headers") else None
    if not is_admin_caller(admin_id):
        return {"status": "forbidden"}
    return {"status": "ok", "users": "see DB", "jobs": "see DB",
            "note": "Wire repositories in main.py for real counts + audit log."}


@router.get("/api/admin/usage")
async def usage(request):
    admin_id = request.headers.get("x-admin-telegram-id") if hasattr(request, "headers") else None
    if not is_admin_caller(admin_id):
        return {"status": "forbidden"}
    return {"status": "ok", "usage": "see usage_daily table"}
