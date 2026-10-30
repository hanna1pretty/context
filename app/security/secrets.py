"""Secret handling: never log values, fail clearly on missing secrets."""
from __future__ import annotations

import os


def mask(value: str | None) -> str:
    if not value:
        return "<missing>"
    if len(value) <= 8:
        return "***"
    return value[:2] + "***" + value[-2:]


def require_env(*names: str) -> dict[str, str]:
    """Return {name: value} or raise listing ONLY the missing names."""
    missing = [n for n in names if not os.environ.get(n)]
    if missing:
        raise RuntimeError(
            "Missing required environment variable(s): " + ", ".join(missing)
            + ". Set them in .env / secret manager; values are never printed."
        )
    return {n: os.environ[n] for n in names}


def redact(text: str, secrets: list[str]) -> str:
    out = text
    for s in secrets:
        if s:
            out = out.replace(s, "***")
    return out
