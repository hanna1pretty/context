"""In-memory daily usage store (production: usage_daily table via repositories).
Pure stdlib; keyed (user_id, date, operation)."""
from __future__ import annotations

from collections import defaultdict


class UsageStore:
    def __init__(self):
        self._data: dict[tuple, dict] = defaultdict(lambda: {"requests": 0, "credits": 0})

    def record(self, user_id: int, date: str, operation: str, credits: int = 0) -> None:
        row = self._data[(user_id, date, operation)]
        row["requests"] += 1
        row["credits"] += credits

    def used_today(self, user_id: int, date: str) -> int:
        return sum(r["requests"] for (u, d, _), r in self._data.items()
                   if u == user_id and d == date)

    def credits_today(self, user_id: int, date: str) -> int:
        return sum(r["credits"] for (u, d, _), r in self._data.items()
                   if u == user_id and d == date)
