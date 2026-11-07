import pytest

from backend.domain.values import parse_submission_value
from config import ConfigError, Settings, load_settings


@pytest.mark.parametrize(("raw", "expected"), [(5, 5.0), ("12.5", 12.5), ("3,5", 3.5), (1e6, 1e6)])
def test_valid_values(raw, expected):
    assert parse_submission_value(raw) == expected


@pytest.mark.parametrize(
    "raw", [None, True, "abc", "", 0, -1, float("nan"), float("inf"), "1e309", 1_000_001, [1]]
)
def test_invalid_values(raw):
    with pytest.raises(ValueError):
        parse_submission_value(raw)


def test_load_settings_from_env(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "1:abc")
    monkeypatch.setenv("ADMIN_IDS", " 1, 2 ,,3")
    monkeypatch.setenv("TIMEZONE", "Europe/Berlin")
    monkeypatch.setenv("INIT_DATA_MAX_AGE", "600")
    monkeypatch.setenv("WEBAPP_URL", "https://x.test/tma/")
    monkeypatch.setenv("FLASK_DEBUG", "true")
    s = load_settings(dotenv=False)
    assert s.admin_ids == frozenset({1, 2, 3})
    assert s.tz.key == "Europe/Berlin"
    assert s.init_data_max_age == 600
    assert s.mini_app_url == "https://x.test/tma"
    assert s.debug is True


def test_defaults(monkeypatch):
    for key in ("BOT_TOKEN", "ADMIN_IDS", "TIMEZONE", "WEBAPP_URL", "PYTHONANYWHERE_DOMAIN"):
        monkeypatch.delenv(key, raising=False)
    s = load_settings(dotenv=False)
    assert s.timezone_name == "Asia/Tashkent"
    assert s.mini_app_url is None


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("ADMIN_IDS", "1,abc"),
        ("TIMEZONE", "Mars/Olympus"),
        ("INIT_DATA_MAX_AGE", "ten"),
        ("INIT_DATA_MAX_AGE", "5"),
        ("ADMIN_API_TOKEN", "short"),
        ("REMINDER_TIME", "9pm"),
    ],
)
def test_invalid_env_raises(monkeypatch, key, value):
    monkeypatch.setenv(key, value)
    with pytest.raises(ConfigError):
        load_settings(dotenv=False)


def test_settings_is_immutable():
    with pytest.raises(AttributeError):
        Settings().bot_token = "x"  # type: ignore[misc]
