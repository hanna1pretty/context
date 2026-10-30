"""Configuration via environment. Pydantic Settings when available, else a
stdlib dataclass fallback with identical field names and validation.
Startup validation fails clearly on missing required secrets WITHOUT
printing their values (see security.secrets)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field

# CONTEXT_DEV_API_KEY is deliberately NOT required: the admin-panel key
# (services/admin_key_service.py, table admin_settings) is now the primary
# input method, and env is only a fallback at call time. Startup must not
# fail when it is missing, or the admin could never set a key via /admin.
REQUIRED_IN_PROD = ["TELEGRAM_BOT_TOKEN", "DATABASE_URL", "REDIS_URL"]


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


def _admin_ids() -> list[int]:
    out = []
    for part in os.environ.get("ADMIN_TELEGRAM_IDS", "").split(","):
        part = part.strip()
        if part.isdigit():
            out.append(int(part))
    return out


@dataclass
class Settings:
    app_env: str = "development"
    app_name: str = "context-intelligence-bot"
    log_level: str = "INFO"
    telegram_bot_token: str = ""
    telegram_webhook_secret: str = ""
    telegram_api_id: str = ""  # only for MTProto; Bot API does NOT need it
    telegram_api_hash: str = ""
    context_dev_api_key: str = ""  # OPTIONAL fallback; admin-panel key is primary
    settings_encryption_key: str = ""  # Fernet key for admin_settings; see README
    context_dev_base_url: str = "https://api.context.dev/v1"
    context_dev_timeout_seconds: float = 60.0
    context_dev_max_concurrency: int = 10
    database_url: str = "postgresql+asyncpg://postgres:postgres@db:5432/context_bot"
    redis_url: str = "redis://redis:6379/0"
    webhook_base_url: str = ""
    webhook_path: str = "/webhooks/telegram"
    context_webhook_secret: str = ""
    admin_telegram_ids: list[int] = field(default_factory=list)
    default_language: str = "id"
    default_timezone: str = "Asia/Jakarta"
    max_telegram_message_length: int = 3900
    max_concurrent_jobs_per_user: int = 2
    max_global_queue_size: int = 10000
    free_daily_limit: int = 10
    pro_daily_limit: int = 100
    business_daily_limit: int = 1000

    def validate(self) -> None:
        # Only TELEGRAM_BOT_TOKEN is required at startup. CONTEXT_DEV_API_KEY
        # is optional: an admin can set it later via /admin, and call time
        # (not startup) is where a missing key is reported to users.
        if self.app_env == "production":
            missing = [n for n in ("TELEGRAM_BOT_TOKEN",)
                       if not getattr(self, n.lower())]
            if missing:
                raise RuntimeError("Missing required secret(s) in production: "
                                   + ", ".join(missing) + " (values not printed)")

    @property
    def is_admin(self):
        return lambda uid: uid in self.admin_telegram_ids


def load_settings() -> Settings:
    return Settings(
        app_env=os.environ.get("APP_ENV", "development"),
        log_level=os.environ.get("LOG_LEVEL", "INFO"),
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        telegram_webhook_secret=os.environ.get("TELEGRAM_WEBHOOK_SECRET", ""),
        telegram_api_id=os.environ.get("TELEGRAM_API_ID", ""),
        telegram_api_hash=os.environ.get("TELEGRAM_API_HASH", ""),
        context_dev_api_key=os.environ.get("CONTEXT_DEV_API_KEY", ""),
        settings_encryption_key=os.environ.get("SETTINGS_ENCRYPTION_KEY", ""),
        context_dev_base_url=os.environ.get("CONTEXT_DEV_BASE_URL", "https://api.context.dev/v1"),
        context_dev_timeout_seconds=float(os.environ.get("CONTEXT_DEV_TIMEOUT_SECONDS", "60")),
        context_dev_max_concurrency=_int("CONTEXT_DEV_MAX_CONCURRENCY", 10),
        database_url=os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/context_bot"),
        redis_url=os.environ.get("REDIS_URL", "redis://redis:6379/0"),
        webhook_base_url=os.environ.get("WEBHOOK_BASE_URL", ""),
        webhook_path=os.environ.get("WEBHOOK_PATH", "/webhooks/telegram"),
        context_webhook_secret=os.environ.get("CONTEXT_WEBHOOK_SECRET", ""),
        admin_telegram_ids=_admin_ids(),
        default_language=os.environ.get("DEFAULT_LANGUAGE", "id"),
        default_timezone=os.environ.get("DEFAULT_TIMEZONE", "Asia/Jakarta"),
        max_telegram_message_length=_int("MAX_TELEGRAM_MESSAGE_LENGTH", 3900),
        max_concurrent_jobs_per_user=_int("MAX_CONCURRENT_JOBS_PER_USER", 2),
        max_global_queue_size=_int("MAX_GLOBAL_QUEUE_SIZE", 10000),
        free_daily_limit=_int("FREE_DAILY_LIMIT", 10),
        pro_daily_limit=_int("PRO_DAILY_LIMIT", 100),
        business_daily_limit=_int("BUSINESS_DAILY_LIMIT", 1000),
    )


# Pydantic Settings mirror (used when pydantic-settings is installed; the
# dataclass above remains the fallback so core modules stay importable).
try:  # pragma: no cover - optional dependency
    from pydantic_settings import BaseSettings as _BaseSettings  # type: ignore

    class PydanticSettings(_BaseSettings):  # type: ignore
        model_config = {"env_file": ".env", "extra": "ignore"}
        APP_ENV: str = "development"
        TELEGRAM_BOT_TOKEN: str = ""
        CONTEXT_DEV_API_KEY: str = ""
        SETTINGS_ENCRYPTION_KEY: str = ""
        DATABASE_URL: str = ""
        REDIS_URL: str = ""
except Exception:  # pragma: no cover
    PydanticSettings = None  # type: ignore
