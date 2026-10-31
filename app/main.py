"""Entry points: FastAPI app (health/webhook/admin) + aiogram bot (polling
for local dev, webhook in production). Heavy imports are lazy so that
``python -m compileall`` and pure tests do not need the full stack installed.

Local (polling):  python -m app.main bot
API only:         uvicorn app.main:create_app --factory --port 8000

Polling wiring (single-process deployment): run_bot_polling starts the
workers/consumer.py loop as an asyncio task in the same process as the
bot. That is what actually turns a queued job into a delivered result;
without it, jobs sat at "memproses..." forever (see workers/consumer.py).
ARQ/Redis is NOT wired for these jobs — see README for that gap.
"""
from __future__ import annotations


def create_app():
    from fastapi import FastAPI  # lazy

    from .api import admin_api, context_webhooks, health

    app = FastAPI(title="Context Intelligence Bot")
    app.include_router(health.router)
    app.include_router(context_webhooks.router)
    app.include_router(admin_api.router)
    return app


async def run_bot_polling():
    """Local-dev polling bot. Production uses webhook (see README)."""
    import asyncio
    import os

    from aiogram import Bot, Dispatcher

    from .bot.router import router
    from .config import load_settings
    from .workers.consumer import consume_forever

    settings = load_settings()
    settings.validate()
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    # Single-process consumer: same process as the bot, so it shares
    # the admin KEY_STORE (in-memory) that /admin writes to. A separate
    # worker process would NOT see that store (documented gap).
    consumer_task = asyncio.create_task(consume_forever(
        bot,
        encryption_key=settings.settings_encryption_key,
        env_key=settings.context_dev_api_key,
    ))
    try:
        await dp.start_polling(bot)
    finally:
        consumer_task.cancel()


if __name__ == "__main__":  # pragma: no cover
    import asyncio
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "bot":
        asyncio.run(run_bot_polling())
    else:
        print("Usage: python -m app.main bot   (API: uvicorn app.main:create_app --factory)")
