"""Bot entry point: ``python -m bot.bot``."""

from __future__ import annotations

import logging
import sys

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, Defaults, MessageHandler, filters

from backend import database
from config import load_settings

from .handlers import cancel, handle_message, start, submit
from .scheduler import setup_jobs

logger = logging.getLogger("bot")


def main() -> int:
    logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s %(message)s", level=logging.INFO)
    # httpx logs every request URL, which contains the bot token.
    logging.getLogger("httpx").setLevel(logging.WARNING)

    settings = load_settings()
    if not settings.bot_token:
        logger.error("BOT_TOKEN is not set; the bot cannot start")
        return 1

    database.init_engine(settings.database_url)
    database.init_db(settings.admin_ids)

    application = (
        ApplicationBuilder()
        .token(settings.bot_token)
        .defaults(Defaults(tzinfo=settings.tz))
        .build()
    )
    application.bot_data["settings"] = settings

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("submit", submit))
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    setup_jobs(application, settings)

    logger.info("bot is starting (timezone=%s)", settings.timezone_name)
    application.run_polling(allowed_updates=Update.ALL_TYPES)
    return 0


if __name__ == "__main__":
    sys.exit(main())
