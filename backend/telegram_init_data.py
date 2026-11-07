"""Validation of Telegram Mini App ``initData``.

Telegram passes a signed query string (``window.Telegram.WebApp.initData``) to
every Mini App. The backend must verify it before trusting *any* user field;
otherwise a client could simply claim to be another user.

Algorithm (https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app):

1. ``data_check_string`` = all received fields except ``hash``, sorted by key,
   formatted as ``key=value`` and joined with ``\\n``.
2. ``secret_key`` = HMAC_SHA256(key="WebAppData", msg=bot_token).
3. The data is authentic iff hex(HMAC_SHA256(key=secret_key, msg=data_check_string)) == hash.
4. ``auth_date`` must be recent, otherwise a leaked initData could be replayed forever.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

# Tolerated clock skew between Telegram and this server for auth_date in the future.
_MAX_FUTURE_SKEW_SECONDS = 60


class InitDataError(Exception):
    """initData is missing, malformed, forged or expired."""


class InitDataSignatureError(InitDataError):
    pass


class InitDataExpiredError(InitDataError):
    pass


@dataclass(frozen=True)
class TelegramUser:
    id: int
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.first_name, self.last_name) if p).strip() or "Unknown"


@dataclass(frozen=True)
class WebAppInitData:
    user: TelegramUser
    auth_date: int
    query_id: str | None = None


def _secret_key(bot_token: str) -> bytes:
    return hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()


def compute_hash(fields: dict[str, str], bot_token: str) -> str:
    """Compute the expected ``hash`` for the given initData fields (``hash`` excluded)."""
    data_check_string = "\n".join(f"{k}={fields[k]}" for k in sorted(fields) if k != "hash")
    return hmac.new(_secret_key(bot_token), data_check_string.encode(), hashlib.sha256).hexdigest()


def _parse_user(raw: str | None) -> TelegramUser:
    if not raw:
        raise InitDataError("initData has no user")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise InitDataError("initData user is not valid JSON") from exc
    if not isinstance(payload, dict):
        raise InitDataError("initData user must be an object")
    user_id = payload.get("id")
    if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
        raise InitDataError("initData user id is invalid")

    def _opt_str(key: str) -> str | None:
        value = payload.get(key)
        return value if isinstance(value, str) and value else None

    return TelegramUser(
        id=user_id,
        first_name=_opt_str("first_name") or "",
        last_name=_opt_str("last_name"),
        username=_opt_str("username"),
        language_code=_opt_str("language_code"),
    )


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 86400,
    now: float | None = None,
) -> WebAppInitData:
    """Verify ``init_data`` and return the authenticated payload.

    Raises :class:`InitDataSignatureError` for a bad/missing hash,
    :class:`InitDataExpiredError` when ``auth_date`` is too old, and
    :class:`InitDataError` for any other malformed input.
    """
    if not bot_token:
        raise InitDataError("bot token is not configured")
    if not init_data or len(init_data) > 8192:
        raise InitDataError("initData is empty or too long")

    try:
        pairs = parse_qsl(init_data, keep_blank_values=True, strict_parsing=True)
    except ValueError as exc:
        raise InitDataError("initData is not a valid query string") from exc

    fields: dict[str, str] = {}
    for key, value in pairs:
        if key in fields:
            raise InitDataError(f"duplicate initData field {key!r}")
        fields[key] = value

    received_hash = fields.get("hash")
    if not received_hash:
        raise InitDataSignatureError("initData hash is missing")
    expected_hash = compute_hash(fields, bot_token)
    if not hmac.compare_digest(expected_hash, received_hash.lower()):
        raise InitDataSignatureError("initData signature mismatch")

    try:
        auth_date = int(fields.get("auth_date", ""))
    except ValueError as exc:
        raise InitDataError("initData auth_date is missing or invalid") from exc
    current = time.time() if now is None else now
    if auth_date > current + _MAX_FUTURE_SKEW_SECONDS:
        raise InitDataError("initData auth_date is in the future")
    if current - auth_date > max_age_seconds:
        raise InitDataExpiredError("initData has expired")

    return WebAppInitData(
        user=_parse_user(fields.get("user")),
        auth_date=auth_date,
        query_id=fields.get("query_id"),
    )
