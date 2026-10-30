"""Error classification for Context.dev. Pure stdlib."""
from __future__ import annotations

from enum import Enum


class ErrorKind(str, Enum):
    RETRYABLE = "retryable"
    VALIDATION = "validation"
    AUTH = "auth"
    PERMISSION = "permission"
    QUOTA = "quota"
    TIMEOUT = "timeout"
    UPSTREAM = "upstream"
    NOT_FOUND = "not_found"
    UNSUPPORTED = "unsupported"  # endpoint not on this account / 404 pattern-inferred


class ContextDevError(Exception):
    def __init__(self, kind: ErrorKind, message: str, *, status: int | None = None,
                 code: str | None = None, retry_after: float | None = None):
        super().__init__(message)
        self.kind = kind
        self.status = status
        self.code = code
        self.retry_after = retry_after

    @property
    def is_retryable(self) -> bool:
        return self.kind in {ErrorKind.RETRYABLE, ErrorKind.TIMEOUT}


def classify_status(status: int, body: str = "") -> ErrorKind:
    if status == 400:
        return ErrorKind.VALIDATION
    if status in (401, 403):
        # 403 can be permission or quota; body hint decides, default permission.
        if "quota" in body.lower() or "credit" in body.lower() or "insufficient" in body.lower():
            return ErrorKind.QUOTA
        return ErrorKind.AUTH if status == 401 else ErrorKind.PERMISSION
    if status == 404:
        return ErrorKind.NOT_FOUND
    if status == 408:
        return ErrorKind.TIMEOUT
    if status == 413:
        return ErrorKind.VALIDATION
    if status == 429:
        return ErrorKind.QUOTA
    if status in (402,):
        return ErrorKind.QUOTA
    if status >= 500:
        return ErrorKind.UPSTREAM
    return ErrorKind.RETRYABLE
