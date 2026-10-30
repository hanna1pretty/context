"""Navigation callbacks + navigation state (back stack).

Screen ids are the canonical vocabulary shared by keyboards, the screens
registry (handlers/navigation.py) and tests. A ``nav:v1:screen:<id>``
callback is only *structurally* validated in base.py; whether the screen
exists is checked against SCREENS in handlers/navigation.py, which falls
back to home for unknown screens.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .base import build, is_expired

MAX_STACK = 10
STATE_TTL_SECONDS = 3600

# Every screen id that any keyboard links to (spec sections 5-18).
SCREEN_IDS = {
    "home", "scrape", "scrape_confirm", "search", "search_results",
    "crawl", "crawl_confirm", "map", "map_results", "answers",
    "answers_result", "parse", "parse_result", "intelligence", "brand",
    "styleguide", "people", "company", "news", "news_results",
    "batches", "job_center", "job_detail", "monitors", "monitor_detail",
    "monitor_delete_confirm", "usage", "plan", "settings",
    "settings_delete_confirm", "settings_clear_confirm", "help",
    "help_commands", "help_examples", "help_status", "help_privacy",
    "admin", "admin_dashboard",
}

# Parent screen for the Kembali button of each screen (home has none).
PARENT_SCREEN: dict[str, str] = {
    "scrape": "home", "search": "home", "crawl": "home", "map": "home",
    "answers": "home", "parse": "home", "intelligence": "home",
    "brand": "intelligence", "styleguide": "intelligence",
    "people": "intelligence", "company": "intelligence",
    "news": "home", "batches": "home", "job_center": "home",
    "job_detail": "job_center", "monitors": "home",
    "monitor_detail": "monitors",
    "monitor_delete_confirm": "monitor_detail",
    "usage": "home", "plan": "usage", "settings": "home",
    "settings_delete_confirm": "settings",
    "settings_clear_confirm": "settings", "help": "home",
    "help_commands": "help", "help_examples": "help", "help_status": "help",
    "help_privacy": "help", "admin": "home", "admin_dashboard": "admin",
    "scrape_confirm": "scrape", "search_results": "search",
    "crawl_confirm": "crawl", "map_results": "map",
    "answers_result": "answers", "parse_result": "parse",
    "news_results": "news",
}


def nav_home() -> str:
    return build("nav", "home")


def nav_back() -> str:
    return build("nav", "back")


def nav_screen(screen: str) -> str:
    return build("nav", "screen", screen)


@dataclass
class NavState:
    """Per-user navigation state: current screen, previous screen and a
    bounded back stack. Expired state falls back to home (never an error
    screen with no way out)."""

    user_id: int
    current_screen: str = "home"
    previous_screen: str = "home"
    stack: list[str] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)
    ttl_seconds: float = STATE_TTL_SECONDS

    def push(self, screen: str, *, now: float | None = None) -> None:
        if screen == self.current_screen:
            return
        self.previous_screen = self.current_screen
        self.stack.append(self.current_screen)
        self.stack = self.stack[-MAX_STACK:]
        self.current_screen = screen
        self.updated_at = now if now is not None else time.time()

    def go_back(self, *, now: float | None = None) -> str:
        if self.is_expired(now=now) or not self.stack:
            self.current_screen = "home"
            self.previous_screen = "home"
            self.stack = []
            return "home"
        self.previous_screen = self.current_screen
        self.current_screen = self.stack.pop()
        self.updated_at = now if now is not None else time.time()
        return self.current_screen

    def go_home(self, *, now: float | None = None) -> str:
        self.current_screen = "home"
        self.previous_screen = "home"
        self.stack = []
        self.updated_at = now if now is not None else time.time()
        return "home"

    def is_expired(self, *, now: float | None = None) -> bool:
        return is_expired(self.updated_at, ttl_seconds=self.ttl_seconds, now=now)

    def parent_of(self, screen: str | None = None) -> str:
        return PARENT_SCREEN.get(screen or self.current_screen, "home")
