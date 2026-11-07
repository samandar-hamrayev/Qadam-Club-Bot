"""Telegram command and message handlers.

The bot talks to the database through :mod:`backend.services` (the same code
path the HTTP API uses), so it never has to forward a user id over HTTP. The
user identity comes from the Telegram update itself, which is trustworthy.
Blocking database work runs in a worker thread to keep the event loop free.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import ContextTypes

from backend import services
from backend.database import session_scope
from backend.domain.values import parse_submission_value
from backend.errors import ServiceError
from config import Settings

from .parsing import parse_challenge_command

logger = logging.getLogger(__name__)

ACTIVE_SUBMISSION_KEY = "active_submission"


def _in_session[T](fn: Callable[..., T], *args: Any) -> T:
    with session_scope() as db:
        return fn(db, *args)


async def run_db[T](fn: Callable[..., T], *args: Any) -> T:
    return await asyncio.to_thread(_in_session, fn, *args)


def _settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return context.application.bot_data["settings"]


def _register(db: Session, telegram_id: int, full_name: str, username: str | None) -> None:
    services.upsert_user(db, telegram_id, full_name, username)


def _active_challenges(db: Session) -> list[dict[str, Any]]:
    return services.list_active_challenges(db)


def _challenge_by_code(db: Session, code: str) -> dict[str, Any] | None:
    challenge = services.get_active_challenge_by_code(db, code)
    return services.challenge_to_dict(challenge) if challenge else None


def _submit(
    db: Session,
    telegram_id: int,
    full_name: str,
    username: str | None,
    challenge_id: int,
    value: str,
    now_local: datetime,
) -> services.SubmissionOutcome:
    user = services.get_user(db, telegram_id) or services.upsert_user(
        db, telegram_id, full_name, username
    )
    return services.submit_result(db, user, challenge_id, value, now_local)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return
    try:
        await run_db(_register, user.id, user.full_name, user.username)
    except Exception:
        logger.exception("failed to register user %s", user.id)
        await message.reply_text("Ro'yxatdan o'tishda xatolik yuz berdi. Keyinroq urinib ko'ring.")
        return

    text = (
        f"Salom, {user.full_name}! 👋\n\n"
        "Qadam Club Botiga xush kelibsiz! Bu yerda siz o'z odatlaringizni "
        "shakllantirishingiz va challenge'larda qatnashishingiz mumkin.\n\n"
    )
    mini_app_url = _settings(context).mini_app_url
    if mini_app_url:
        markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Open Mini App", web_app=WebAppInfo(url=mini_app_url))]]
        )
        await message.reply_text(text + "Boshlash uchun Mini App'ni oching!", reply_markup=markup)
    else:
        await message.reply_text(text + "Natija topshirish uchun /submit buyrug'idan foydalaning.")


async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    try:
        challenges = await run_db(_active_challenges)
    except Exception:
        logger.exception("failed to load challenges")
        await message.reply_text("Challenge'larni olishda xatolik!")
        return
    if not challenges:
        await message.reply_text("Hozircha faol challenge'lar yo'q.")
        return
    lines = ["Qaysi challenge uchun natija topshirmoqchisiz?", ""]
    lines += [f"/{c['code']} - {c['title']}" for c in challenges]
    lines += ["", "Masalan: /" + challenges[0]["code"] + " 10"]
    await message.reply_text("\n".join(lines))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None or not message.text:
        return
    text = message.text.strip()
    user_data = context.user_data if context.user_data is not None else {}

    command = parse_challenge_command(text)
    if command is not None:
        challenge = await run_db(_challenge_by_code, command.code)
        if challenge is None:
            if ACTIVE_SUBMISSION_KEY in user_data:
                await message.reply_text("Iltimos, faqat son kiriting (yoki /cancel deb yozing).")
            return
        if command.value is not None:
            user_data.pop(ACTIVE_SUBMISSION_KEY, None)
            await _process_submission(update, context, challenge["id"], command.value)
            return
        user_data[ACTIVE_SUBMISSION_KEY] = challenge["id"]
        await message.reply_text(
            f"{challenge['title']} uchun natijani kiriting "
            f"({challenge['target_unit']}, masalan: 10):"
        )
        return

    if ACTIVE_SUBMISSION_KEY in user_data:
        try:
            parse_submission_value(text)
        except ValueError:
            # Keep waiting for a valid number instead of dropping the user's context.
            await message.reply_text("Iltimos, musbat son kiriting (yoki /cancel deb yozing).")
            return
        challenge_id = user_data.pop(ACTIVE_SUBMISSION_KEY)
        await _process_submission(update, context, challenge_id, text)


async def _process_submission(
    update: Update, context: ContextTypes.DEFAULT_TYPE, challenge_id: int, value: str
) -> None:
    user = update.effective_user
    message = update.effective_message
    if user is None or message is None:
        return
    now_local = datetime.now(_settings(context).tz)
    try:
        outcome = await run_db(
            _submit, user.id, user.full_name, user.username, challenge_id, value, now_local
        )
    except ServiceError as exc:
        await message.reply_text(f"Xato: {exc.message}")
        return
    except Exception:
        logger.exception("submission failed for user %s", user.id)
        await message.reply_text("Topshirishda xatolik yuz berdi.")
        return
    await message.reply_text(
        "Muvaffaqiyatli qabul qilindi! ✅\n"
        f"Streak: {outcome.current_streak} kun\n"
        f"Jami: {outcome.total_value:g}"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if message is None:
        return
    user_data = context.user_data if context.user_data is not None else {}
    if user_data.pop(ACTIVE_SUBMISSION_KEY, None) is not None:
        await message.reply_text("Bekor qilindi. ❌")
    else:
        await message.reply_text("Hozircha bekor qiladigan narsa yo'q.")
