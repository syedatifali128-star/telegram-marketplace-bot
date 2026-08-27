"""
Standalone entrypoint for the Telegram bot (polling mode for V1).

Run separately from the FastAPI dashboard/API process:
    python -m app.bot.run_bot

Kept as its own process rather than bolted onto the FastAPI app so the
bot's event loop and the web server don't have to share one process —
simpler to reason about, restart independently, and matches the
Dockerfile/docker-compose setup added in the deployment phase.
"""
from __future__ import annotations

import logging

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from app.config import settings
from app.database.connection import init_db
from app.bot.handlers import customer
from app.services.scheduler_service import build_scheduler, start_scheduler

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("app.bot")


def build_application() -> Application:
    if not settings.bot_token:
        raise RuntimeError("BOT_TOKEN is not set — add it to your .env file (see .env.example).")

    application = Application.builder().token(settings.bot_token).build()

    application.add_handler(CommandHandler("start", customer.start))
    application.add_handler(CommandHandler("cancel", customer.cancel))
    application.add_handler(CallbackQueryHandler(customer.callback_router))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, customer.text_message_router))

    return application


async def _on_startup(application: Application) -> None:
    """Starts the campaign scheduler inside the bot's own asyncio event loop."""
    scheduler = build_scheduler()
    start_scheduler(scheduler, application.bot)
    application.bot_data["scheduler"] = scheduler
    logger.info("Campaign scheduler attached to bot event loop.")


def main() -> None:
    init_db()
    application = build_application()
    application.post_init = _on_startup
    logger.info("Bot starting (polling mode)...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
