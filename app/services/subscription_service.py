"""Entitlement, server-side. Pure stdlib. Bot billing != Context.dev credits."""
from __future__ import annotations

from dataclasses import dataclass

PLANS = {
    "free": {"daily_limit": 10, "max_active_jobs": 2, "max_crawl_pages": 20,
             "export": False, "monitors": 0, "retention_days": 3, "priority": 0},
    "pro": {"daily_limit": 100, "max_active_jobs": 5, "max_crawl_pages": 200,
            "export": True, "monitors": 5, "retention_days": 30, "priority": 1},
    "business": {"daily_limit": 1000, "max_active_jobs": 20, "max_crawl_pages": 500,
                 "export": True, "monitors": 50, "retention_days": 90, "priority": 2},
}
# Features gated by plan (free = scrape/search only, per spec section 11).
FEATURE_MIN_PLAN = {
    "scrape": "free", "search": "free", "news": "free",
    "crawl": "pro", "map": "pro", "parse": "pro", "answers": "pro",
    "brand": "pro", "styleguide": "pro", "people": "business",
    "company": "pro", "batches": "pro", "monitors": "pro",
}
_PLAN_RANK = {"free": 0, "pro": 1, "business": 2}


@dataclass
class Entitlement:
    plan: str
    allowed: bool
    reason: str = ""


def plan_limits(plan: str) -> dict:
    return PLANS.get(plan, PLANS["free"])


def check_feature(plan: str, feature: str) -> Entitlement:
    need = FEATURE_MIN_PLAN.get(feature, "free")
    if _PLAN_RANK.get(plan, 0) >= _PLAN_RANK[need]:
        return Entitlement(plan, True)
    return Entitlement(plan, False, f"feature '{feature}' requires {need} plan")


def check_daily_quota(plan: str, used_today: int) -> Entitlement:
    limit = plan_limits(plan)["daily_limit"]
    if used_today < limit:
        return Entitlement(plan, True)
    return Entitlement(plan, False, f"daily limit reached ({limit}/day)")


def is_admin(telegram_user_id: int, admin_ids: list[int]) -> bool:
    return telegram_user_id in admin_ids
