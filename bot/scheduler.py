"""Scheduled jobs, run by PTB's JobQueue (APScheduler under the hood).

All schedules use the configured club timezone, not the server's local time.
"""

from __future__ import annotations

import logging
from datetime import datetime, time
from pathlib import Path

from telegram.error import Forbidden, TelegramError
from telegram.ext import Application, ContextTypes

from backend import services
from backend.domain.window import parse_hhmm
from config import Settings

from .handlers import run_db

logger = logging.getLogger(__name__)

HEARTBEAT_FILE = Path("/tmp/qadam-bot.heartbeat")
MONDAY = 1  # PTB >= 20 numbers days 0-6 as Sunday-Saturday


def _settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return context.application.bot_data["settings"]


async def _safe_send(context: ContextTypes.DEFAULT_TYPE, chat_id: int, text: str) -> bool:
    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
        return True
    except Forbidden:
        logger.info("user %s blocked the bot; skipping", chat_id)
    except TelegramError:
        logger.exception("failed to send message to %s", chat_id)
    return False


async def send_daily_reminders(context: ContextTypes.DEFAULT_TYPE) -> None:
    now_local = datetime.now(_settings(context).tz)
    reminders = await run_db(services.pending_reminders, now_local)
    sent = 0
    for reminder in reminders:
        sent += await _safe_send(
            context,
            reminder.telegram_id,
            f"🔔 Eslatma: bugun '{reminder.challenge_title}' challenge uchun "
            "natija topshirishni unutmang!",
        )
    logger.info("daily reminders: %d/%d delivered", sent, len(reminders))


async def announce_weekly_winners(context: ContextTypes.DEFAULT_TYPE) -> None:
    today = datetime.now(_settings(context).tz).date()
    winners = await run_db(services.record_weekly_results, today)
    for w in winners:
        await _safe_send(
            context,
            w.telegram_id,
            f"🏆 Tabriklaymiz, {w.full_name}! Siz {w.week_start:%d.%m.%Y} haftasida "
            f"'{w.challenge_title}' challenge g'olibisiz: {w.total:g} {w.target_unit}.",
        )
    logger.info("weekly results recorded; %d winner(s) notified", len(winners))


async def heartbeat(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Touch a file so the container healthcheck can tell the loop is alive."""
    HEARTBEAT_FILE.touch()


def setup_jobs(application: Application, settings: Settings) -> None:
    job_queue = application.job_queue
    if job_queue is None:  # pragma: no cover - requires the [job-queue] extra
        raise RuntimeError("python-telegram-bot[job-queue] is required")
    tz = settings.tz
    reminder_at = parse_hhmm(settings.reminder_time).replace(tzinfo=tz)
    job_queue.run_daily(send_daily_reminders, time=reminder_at, name="daily-reminders")
    job_queue.run_daily(
        announce_weekly_winners,
        time=time(0, 5, tzinfo=tz),
        days=(MONDAY,),
        name="weekly-winners",
    )
    job_queue.run_repeating(heartbeat, interval=30, first=0, name="heartbeat")
