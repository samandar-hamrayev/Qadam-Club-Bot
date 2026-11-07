"""Request authentication for the Flask API.

* Mini App endpoints: ``Authorization: tma <initData>``. The user identity is
  taken *only* from the validated, HMAC-signed initData -- never from the
  request body or query string.
* Admin endpoints: ``Authorization: Bearer <ADMIN_API_TOKEN>`` (constant-time
  comparison), or a valid ``tma`` initData whose user is listed in ADMIN_IDS.
"""

from __future__ import annotations

import hmac
import logging
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any, cast

from flask import current_app, g, request
from sqlalchemy.orm import Session

from config import Settings

from . import services
from .database import session_scope
from .errors import Forbidden, ServiceUnavailable, Unauthorized
from .models import User
from .telegram_init_data import (
    InitDataError,
    InitDataExpiredError,
    WebAppInitData,
    validate_init_data,
)

logger = logging.getLogger(__name__)


def get_settings() -> Settings:
    return current_app.config["SETTINGS"]


def now_local() -> datetime:
    """Current time in the club timezone (overridable in tests via ``CLOCK``)."""
    return current_app.config["CLOCK"]()


def _authorization() -> tuple[str, str]:
    header = request.headers.get("Authorization", "")
    scheme, _, credentials = header.partition(" ")
    return scheme.strip().lower(), credentials.strip()


def _validate_tma(credentials: str) -> WebAppInitData:
    settings = get_settings()
    if not settings.bot_token:
        logger.error("BOT_TOKEN is not configured; cannot validate Mini App initData")
        raise ServiceUnavailable("Mini App authentication is not configured")
    try:
        return validate_init_data(
            credentials, settings.bot_token, max_age_seconds=settings.init_data_max_age
        )
    except InitDataExpiredError as exc:
        raise Unauthorized("Telegram session expired, reopen the Mini App") from exc
    except InitDataError as exc:
        logger.info("rejected initData: %s", exc)
        raise Unauthorized("Invalid Telegram initData") from exc


def require_tma_user[F: Callable[..., Any]](fn: F) -> F:
    """Require a valid Telegram Mini App ``initData``; exposes it as ``g.init_data``."""

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        scheme, credentials = _authorization()
        if scheme != "tma" or not credentials:
            raise Unauthorized("Telegram Mini App authorization required")
        g.init_data = _validate_tma(credentials)
        return fn(*args, **kwargs)

    return cast(F, wrapper)


def current_user(db: Session) -> User:
    """The authenticated Telegram user, registering them on first contact."""
    tg_user = g.init_data.user
    user = services.get_user(db, tg_user.id)
    if user is None:
        user = services.upsert_user(db, tg_user.id, tg_user.full_name, tg_user.username)
    return user


def require_admin[F: Callable[..., Any]](fn: F) -> F:
    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        scheme, credentials = _authorization()
        settings = get_settings()
        if scheme == "bearer" and credentials:
            expected = settings.admin_api_token
            if expected and hmac.compare_digest(credentials.encode(), expected.encode()):
                g.admin = "token"
                return fn(*args, **kwargs)
            raise Unauthorized("Invalid admin token")
        if scheme == "tma" and credentials:
            init_data = _validate_tma(credentials)
            with session_scope() as db:
                if not services.is_admin(db, init_data.user.id):
                    raise Forbidden("Admin privileges required")
            g.init_data = init_data
            g.admin = f"telegram:{init_data.user.id}"
            return fn(*args, **kwargs)
        raise Unauthorized("Admin authorization required")

    return cast(F, wrapper)
