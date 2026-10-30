"""Structured JSON logging, stdlib only. Telegram user IDs are pseudonymised."""
from __future__ import annotations

import hashlib
import json
import logging
import sys


def pseudonymise_user_id(user_id: int | None) -> str | None:
    if user_id is None:
        return None
    return "u_" + hashlib.sha256(str(user_id).encode()).hexdigest()[:12]


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {"level": record.levelname, "logger": record.name,
                   "message": record.getMessage()}
        for key in ("trace_id", "job_id", "endpoint", "status", "latency_ms",
                    "error_code", "telegram_user_id"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str = "INFO") -> logging.Logger:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger("context_bot")
    root.handlers = [handler]
    root.setLevel(level.upper())
    return root
