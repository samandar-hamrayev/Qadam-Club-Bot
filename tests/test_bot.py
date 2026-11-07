"""Bot handlers and jobs, exercised with fakes -- the Telegram API is never called."""

import asyncio
from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from telegram.error import Forbidden

from backend.database import session_scope
from backend.models import Submission, User
from bot import handlers, scheduler
from bot.parsing import ChallengeCommand, parse_challenge_command


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("/book", ChallengeCommand("book")),
        ("/book 25", ChallengeCommand("book", "25")),
        ("/Book@QadamBot 25", ChallengeCommand("book", "25")),
        ("25", None),
        ("/", None),
        ("", None),
        ("/@bot", None),
    ],
)
def test_parse_challenge_command(text, expected):
    assert parse_challenge_command(text) == expected


class FakeMessage:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self.replies: list[str] = []
        self.reply_text = AsyncMock(side_effect=lambda text, **kw: self.replies.append(text))


def make_update(text: str = "", user_id: int = 42):
    user = SimpleNamespace(id=user_id, full_name="Ali Valiyev", username="ali")
    message = FakeMessage(text)
    return SimpleNamespace(effective_user=user, effective_message=message), message


@pytest.fixture
def context(settings):
    return SimpleNamespace(
        user_data={},
        application=SimpleNamespace(bot_data={"settings": settings}),
        bot=SimpleNamespace(send_message=AsyncMock()),
    )


def run(coro):
    return asyncio.run(coro)


def test_start_registers_user_and_offers_mini_app(app, context):
    update, message = make_update("/start")
    run(handlers.start(update, context))
    with session_scope() as db:
        assert db.query(User).filter_by(telegram_id=42).one().full_name == "Ali Valiyev"
    markup = message.reply_text.call_args.kwargs["reply_markup"]
    assert markup.inline_keyboard[0][0].web_app.url == "https://example.test/tma"


def test_submit_lists_challenges(app, context, make_challenge):
    update, message = make_update("/submit")
    run(handlers.submit(update, context))
    assert "yo'q" in message.replies[-1]
    make_challenge("book", title="Kitob")
    run(handlers.submit(update, context))
    assert "/book - Kitob" in message.replies[-1]


def test_inline_command_submission(app, context, make_challenge):
    make_challenge("book")
    update, message = make_update("/book 15")
    run(handlers.handle_message(update, context))
    assert "Streak: 1 kun" in message.replies[-1]
    # Second submission the same day is refused by the shared service layer.
    run(handlers.handle_message(update, context))
    assert message.replies[-1].startswith("Xato: Already submitted today")


def test_two_step_submission_keeps_state_on_bad_input(app, context, make_challenge):
    make_challenge("steps")
    update, message = make_update("/steps")
    run(handlers.handle_message(update, context))
    assert handlers.ACTIVE_SUBMISSION_KEY in context.user_data

    update, message = make_update("abc")
    run(handlers.handle_message(update, context))
    assert "musbat son" in message.replies[-1]
    assert handlers.ACTIVE_SUBMISSION_KEY in context.user_data

    update, message = make_update("7000")
    run(handlers.handle_message(update, context))
    assert "Muvaffaqiyatli" in message.replies[-1]
    assert handlers.ACTIVE_SUBMISSION_KEY not in context.user_data
    with session_scope() as db:
        assert db.query(Submission).one().value == 7000


def test_cancel(app, context):
    update, message = make_update("/cancel")
    run(handlers.cancel(update, context))
    assert "yo'q" in message.replies[-1]
    context.user_data[handlers.ACTIVE_SUBMISSION_KEY] = 1
    run(handlers.cancel(update, context))
    assert "Bekor" in message.replies[-1]


def test_reminder_job_sends_and_tolerates_blocked_users(app, context, client, make_challenge):
    from tests.conftest import tma

    cid = make_challenge("steps")
    for uid in (1, 2):
        client.post(f"/api/challenges/{cid}/join", headers=tma(uid))
    context.bot.send_message.side_effect = [Forbidden("blocked"), None]
    run(scheduler.send_daily_reminders(context))
    assert context.bot.send_message.await_count == 2


def test_weekly_job_notifies_winner(app, context, client, make_challenge, clock, monkeypatch):
    from tests.conftest import tma

    cid = make_challenge("steps")
    clock.set(2026, 3, 3, 12, 0)
    client.post(f"/api/challenges/{cid}/submit", headers=tma(5), json={"value": 10})

    class FrozenDatetime:
        @staticmethod
        def now(tz):
            from datetime import datetime

            return datetime(2026, 3, 9, 0, 5, tzinfo=tz)

    monkeypatch.setattr(scheduler, "datetime", FrozenDatetime)
    run(scheduler.announce_weekly_winners(context))
    kwargs = context.bot.send_message.call_args.kwargs
    assert kwargs["chat_id"] == 5
    assert "02.03.2026" in kwargs["text"]
    assert date(2026, 3, 9).weekday() == 0


def test_setup_jobs_uses_club_timezone(settings):
    from telegram.ext import ApplicationBuilder

    application = ApplicationBuilder().token("123:TEST").build()
    scheduler.setup_jobs(application, settings)
    names = {job.name for job in application.job_queue.jobs()}
    assert names == {"daily-reminders", "weekly-winners", "heartbeat"}


def test_bot_refuses_to_start_without_token(monkeypatch):
    from bot import bot as bot_main
    from config import Settings

    monkeypatch.setattr(bot_main, "load_settings", lambda: Settings(bot_token=None))
    assert bot_main.main() == 1
