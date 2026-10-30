"""Entry points: FastAPI app (health/webhook/admin) + aiogram bot (polling
for local dev, webhook in production). Heavy imports are lazy so that
`python -m compileall` and pure tests do not need the full stack installed.

Local (polling):  python -m app.main bot
API only:         uvicorn app.main:create_app --factory --port 8000
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
    import os

    from aiogram import Bot, Dispatcher

    from .bot.router import router
    from .config import load_settings

    settings = load_settings()
    settings.validate()
    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":  # pragma: no cover
    import asyncio
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "bot":
        asyncio.run(run_bot_polling())
    else:
        print("Usage: python -m app.main bot   (API: uvicorn app.main:create_app --factory)")
