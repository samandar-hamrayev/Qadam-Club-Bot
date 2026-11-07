from __future__ import annotations

import json
import time
from datetime import datetime
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

import pytest

from backend.app import create_app
from backend.database import session_scope
from backend.models import Challenge
from backend.telegram_init_data import compute_hash
from config import Settings

BOT_TOKEN = "123456:TEST-ONLY-NOT-A-REAL-TOKEN"
ADMIN_TOKEN = "test-admin-token-0123456789abcdef"
ADMIN_TG_ID = 999
TZ = ZoneInfo("Asia/Tashkent")


def make_init_data(
    user_id: int = 42,
    first_name: str = "Ali",
    *,
    username: str | None = "ali",
    auth_date: int | None = None,
    bot_token: str = BOT_TOKEN,
    extra: dict[str, str] | None = None,
) -> str:
    """Build initData signed exactly like Telegram does."""
    user = {"id": user_id, "first_name": first_name}
    if username:
        user["username"] = username
    fields = {
        "query_id": "AAH-test",
        "user": json.dumps(user, separators=(",", ":")),
        "auth_date": str(int(time.time()) if auth_date is None else auth_date),
    }
    fields.update(extra or {})
    fields["hash"] = compute_hash(fields, bot_token)
    return urlencode(fields)


def tma(user_id: int = 42, **kwargs) -> dict[str, str]:
    return {"Authorization": f"tma {make_init_data(user_id, **kwargs)}"}


ADMIN_HEADERS = {"Authorization": f"Bearer {ADMIN_TOKEN}"}


class FakeClock:
    def __init__(self, now: datetime) -> None:
        self.now = now

    def set(self, *args: int) -> None:
        self.now = datetime(*args, tzinfo=TZ)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture
def settings() -> Settings:
    return Settings(
        bot_token=BOT_TOKEN,
        admin_ids=frozenset({ADMIN_TG_ID}),
        admin_api_token=ADMIN_TOKEN,
        database_url="sqlite://",
        timezone_name="Asia/Tashkent",
        webapp_url="https://example.test",
    )


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(datetime(2026, 3, 10, 12, 0, tzinfo=TZ))


@pytest.fixture
def app(settings, clock):
    app = create_app(settings, clock=clock)
    app.config["TESTING"] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def make_challenge(app):
    def _make(code: str = "steps", start: str | None = None, end: str | None = None, **kw):
        with session_scope() as db:
            challenge = Challenge(
                title=kw.pop("title", code.title()),
                code=code,
                target_unit=kw.pop("target_unit", "units"),
                time_window_start=start,
                time_window_end=end,
                **kw,
            )
            db.add(challenge)
            db.flush()
            return challenge.id

    return _make
