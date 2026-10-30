"""Callback package: central parser/validator + per-feature builders."""
from __future__ import annotations

from .base import (
    LEGACY_CALLBACKS,
    MAX_CALLBACK_BYTES,
    NAMESPACES,
    CallbackParts,
    CursorStore,
    DoubleClickGuard,
    build,
    check_owner,
    is_expired,
    is_legacy,
    is_recognized,
    parse_callback,
    validate_callback,
)
from .navigation import SCREEN_IDS, NavState, nav_back, nav_home, nav_screen

__all__ = [
    "LEGACY_CALLBACKS", "MAX_CALLBACK_BYTES", "NAMESPACES", "CallbackParts",
    "CursorStore", "DoubleClickGuard", "build", "check_owner", "is_expired",
    "is_legacy", "is_recognized", "parse_callback", "validate_callback",
    "SCREEN_IDS", "NavState", "nav_back", "nav_home", "nav_screen",
]
