"""Credit estimation from the task's pricing anchors. Estimates only:
actual consumption comes from key_metadata.credits_consumed in responses."""
from __future__ import annotations

from ..contextdev.endpoint_router import endpoint_for

FEATURE_PAGES_MULTIPLIER = {"crawl": 1, "map": 1}


def estimate_credits(feature: str, *, pages: int = 1) -> int:
    ep = endpoint_for(feature)
    if feature in ("crawl", "map"):
        return ep.min_credits * max(1, pages)
    return ep.min_credits


def cost_guard_ok(feature: str, *, pages: int, plan_max_pages: int) -> tuple[bool, str]:
    if feature == "crawl" and pages > plan_max_pages:
        return False, f"crawl page limit for your plan is {plan_max_pages}, requested {pages}"
    return True, ""
