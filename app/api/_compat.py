"""FastAPI compatibility shim (same idea as bot/_compat.py)."""
from __future__ import annotations


def _noop(*a, **k):
    def wrap(fn):
        return fn
    return wrap


try:
    from fastapi import APIRouter as _Real  # type: ignore

    def get_router():
        return _Real()
except Exception:  # pragma: no cover
    class _Stub:
        get = post = _noop
        def include_router(self, other):
            pass

    def get_router():
        return _Stub()
