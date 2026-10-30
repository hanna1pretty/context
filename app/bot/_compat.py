"""aiogram compatibility shim: real Router when aiogram is installed,
otherwise a no-op decorator router so modules stay importable/syntax-checked."""
from __future__ import annotations


def _noop_decorator(*args, **kwargs):
    def wrap(fn):
        return fn
    return wrap


try:
    from aiogram import Router as _RealRouter  # type: ignore

    def get_router():
        return _RealRouter()
except Exception:  # pragma: no cover
    class _StubRouter:
        message = staticmethod(_noop_decorator)
        callback_query = staticmethod(_noop_decorator)
        def include_router(self, other):
            pass

    def get_router():
        return _StubRouter()
