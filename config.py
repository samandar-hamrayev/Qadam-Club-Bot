"""Application settings, loaded exclusively from environment variables.

Both the Flask API and the Telegram bot read their configuration through
:func:`load_settings`. A local ``.env`` file is honoured for development
convenience (via python-dotenv); in production the variables are expected to
come from the process environment (Docker, systemd, PaaS, ...).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from dotenv import load_dotenv

DEFAULT_TIMEZONE = "Asia/Tashkent"
DEFAULT_DATABASE_URL = "sqlite:///qadam_club.db"
MIN_ADMIN_TOKEN_LENGTH = 24


class ConfigError(ValueError):
    """Raised when an environment variable has an invalid value."""


def _parse_admin_ids(raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError as exc:
            raise ConfigError(f"ADMIN_IDS must be comma-separated integers, got {part!r}") from exc
    return frozenset(ids)


def _parse_int(name: str, raw: str | None, default: int, minimum: int = 0) -> int:
    if raw is None or raw.strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ConfigError(f"{name} must be >= {minimum}")
    return value


def _parse_bool(raw: str | None, default: bool = False) -> bool:
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    """Immutable runtime configuration."""

    bot_token: str | None = None
    admin_ids: frozenset[int] = field(default_factory=frozenset)
    admin_api_token: str | None = None
    database_url: str = DEFAULT_DATABASE_URL
    timezone_name: str = DEFAULT_TIMEZONE
    webapp_url: str | None = None
    init_data_max_age: int = 86400
    reminder_time: str = "21:00"
    debug: bool = False

    def __post_init__(self) -> None:
        try:
            ZoneInfo(self.timezone_name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ConfigError(f"Unknown TIMEZONE {self.timezone_name!r}") from exc
        if self.admin_api_token is not None and len(self.admin_api_token) < MIN_ADMIN_TOKEN_LENGTH:
            raise ConfigError(
                f"ADMIN_API_TOKEN must be at least {MIN_ADMIN_TOKEN_LENGTH} characters long"
            )
        # Validated lazily to avoid a circular import with the domain package.
        from backend.domain.window import parse_hhmm

        try:
            parse_hhmm(self.reminder_time)
        except ValueError as exc:
            raise ConfigError("REMINDER_TIME must be in HH:MM format") from exc

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone_name)

    @property
    def mini_app_url(self) -> str | None:
        """Public HTTPS URL of the Mini App page (``<WEBAPP_URL>/tma``)."""
        if not self.webapp_url:
            return None
        base = self.webapp_url.rstrip("/")
        if base.endswith("/tma"):
            base = base[: -len("/tma")]
        return f"{base}/tma"


def load_settings(*, dotenv: bool = True) -> Settings:
    """Build :class:`Settings` from the process environment."""
    if dotenv:
        load_dotenv()
    env = os.environ
    return Settings(
        bot_token=env.get("BOT_TOKEN") or None,
        admin_ids=_parse_admin_ids(env.get("ADMIN_IDS", "")),
        admin_api_token=env.get("ADMIN_API_TOKEN") or None,
        database_url=env.get("DATABASE_URL") or DEFAULT_DATABASE_URL,
        timezone_name=env.get("TIMEZONE") or DEFAULT_TIMEZONE,
        # PYTHONANYWHERE_DOMAIN is accepted for backwards compatibility.
        webapp_url=env.get("WEBAPP_URL") or env.get("PYTHONANYWHERE_DOMAIN") or None,
        init_data_max_age=_parse_int(
            "INIT_DATA_MAX_AGE", env.get("INIT_DATA_MAX_AGE"), 86400, minimum=60
        ),
        reminder_time=env.get("REMINDER_TIME") or "21:00",
        debug=_parse_bool(env.get("FLASK_DEBUG")),
    )
