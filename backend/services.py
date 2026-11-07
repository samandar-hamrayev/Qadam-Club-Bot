"""Application services: the only place that combines domain rules with the database.

Both the Flask routes and the Telegram bot call these functions, so business
rules (submission window, one submission per day, streaks, rankings) live in
exactly one place. Every function receives an open SQLAlchemy session; the
caller owns the transaction (see :func:`backend.database.session_scope`).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from sqlalchemy import exists, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .domain.ranking import current_week_start, previous_week, rank_totals
from .domain.streaks import compute_streaks, effective_streak
from .domain.values import parse_submission_value
from .domain.window import SubmissionWindow, challenge_day, is_submission_open
from .errors import Conflict, Forbidden, NotFound, SubmissionWindowClosed, ValidationError
from .models import AdminUser, Challenge, Submission, User, UserChallenge, WeeklyResult

logger = logging.getLogger(__name__)

LEADERBOARD_PERIODS = ("today", "weekly", "monthly", "all")
LEADERBOARD_LIMIT = 10


# --------------------------------------------------------------------------- users


def upsert_user(db: Session, telegram_id: int, full_name: str, username: str | None) -> User:
    """Create the user or refresh their profile from Telegram-verified data."""
    full_name = (full_name or "Unknown").strip()[:255] or "Unknown"
    username = username[:255] if username else None
    user = db.scalar(select(User).where(User.telegram_id == telegram_id))
    if user is None:
        user = User(telegram_id=telegram_id, full_name=full_name, username=username)
        db.add(user)
    else:
        user.full_name = full_name
        user.username = username
    db.flush()
    return user


def get_user(db: Session, telegram_id: int) -> User | None:
    return db.scalar(select(User).where(User.telegram_id == telegram_id))


def require_user(db: Session, telegram_id: int) -> User:
    user = get_user(db, telegram_id)
    if user is None:
        raise NotFound("User is not registered")
    return user


def is_admin(db: Session, telegram_id: int) -> bool:
    return db.scalar(select(exists().where(AdminUser.telegram_id == telegram_id))) or False


def user_to_dict(user: User, *, is_admin: bool | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": user.id,
        "telegram_id": user.telegram_id,
        "full_name": user.full_name,
        "username": user.username,
        "is_active": user.is_active,
        "is_banned": user.is_banned,
    }
    if is_admin is not None:
        data["is_admin"] = is_admin
    return data


# ---------------------------------------------------------------------- challenges


def challenge_window(challenge: Challenge) -> SubmissionWindow | None:
    try:
        return SubmissionWindow.parse(challenge.time_window_start, challenge.time_window_end)
    except ValueError:
        # Legacy rows written before input validation existed: fail open, but loudly.
        logger.warning("challenge %s has an invalid time window; ignoring it", challenge.id)
        return None


def challenge_to_dict(challenge: Challenge, *, is_joined: bool | None = None) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": challenge.id,
        "title": challenge.title,
        "description": challenge.description,
        "code": challenge.code,
        "target_unit": challenge.target_unit,
        "time_window_start": challenge.time_window_start,
        "time_window_end": challenge.time_window_end,
        "is_active": challenge.is_active,
    }
    if is_joined is not None:
        data["is_joined"] = is_joined
    return data


def list_active_challenges(db: Session, user: User | None = None) -> list[dict[str, Any]]:
    challenges = db.scalars(
        select(Challenge).where(Challenge.is_active.is_(True)).order_by(Challenge.id)
    ).all()
    joined: set[int] = set()
    if user is not None:
        joined = set(
            db.scalars(
                select(UserChallenge.challenge_id).where(
                    UserChallenge.user_id == user.id, UserChallenge.is_joined.is_(True)
                )
            )
        )
    return [
        challenge_to_dict(c, is_joined=(c.id in joined) if user is not None else None)
        for c in challenges
    ]


def get_active_challenge(db: Session, challenge_id: int) -> Challenge:
    challenge = db.get(Challenge, challenge_id)
    if challenge is None or not challenge.is_active:
        raise NotFound("Challenge not found")
    return challenge


def get_active_challenge_by_code(db: Session, code: str) -> Challenge | None:
    return db.scalar(select(Challenge).where(Challenge.code == code, Challenge.is_active.is_(True)))


def _get_user_challenge(db: Session, user_id: int, challenge_id: int) -> UserChallenge | None:
    return db.scalar(
        select(UserChallenge).where(
            UserChallenge.user_id == user_id, UserChallenge.challenge_id == challenge_id
        )
    )


def join_challenge(db: Session, user: User, challenge_id: int) -> UserChallenge:
    if user.is_banned:
        raise Forbidden("User is banned")
    get_active_challenge(db, challenge_id)
    membership = _get_user_challenge(db, user.id, challenge_id)
    if membership is None:
        membership = UserChallenge(
            user_id=user.id,
            challenge_id=challenge_id,
            is_joined=True,
            current_streak=0,
            max_streak=0,
            total_value=0.0,
        )
        db.add(membership)
    else:
        membership.is_joined = True
    db.flush()
    return membership


# --------------------------------------------------------------------- submissions


@dataclass(frozen=True)
class SubmissionOutcome:
    challenge_id: int
    day: date
    value: float
    current_streak: int
    max_streak: int
    total_value: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "success",
            "challenge_id": self.challenge_id,
            "date": self.day.isoformat(),
            "value": self.value,
            "current_streak": self.current_streak,
            "max_streak": self.max_streak,
            "total_value": self.total_value,
        }


def submit_result(
    db: Session, user: User, challenge_id: int, raw_value: object, now_local: datetime
) -> SubmissionOutcome:
    """Record today's result for a challenge and update the streak.

    ``now_local`` must be an aware datetime in the club timezone.
    """
    if user.is_banned:
        raise Forbidden("User is banned")
    challenge = get_active_challenge(db, challenge_id)

    try:
        value = parse_submission_value(raw_value)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc

    window = challenge_window(challenge)
    if not is_submission_open(window, now_local):
        raise SubmissionWindowClosed(f"Submissions are only accepted between {window}")
    day = challenge_day(now_local, window)

    already = db.scalar(
        select(
            exists().where(
                Submission.user_id == user.id,
                Submission.challenge_id == challenge_id,
                Submission.date == day,
            )
        )
    )
    if already:
        raise Conflict("Already submitted today")

    membership = _get_user_challenge(db, user.id, challenge_id)
    if membership is None:
        membership = join_challenge(db, user, challenge_id)
    membership.is_joined = True

    db.add(
        Submission(
            user_id=user.id,
            challenge_id=challenge_id,
            value=value,
            date=day,
            submitted_at=now_local,
        )
    )
    try:
        db.flush()
    except IntegrityError as exc:  # concurrent duplicate caught by the unique constraint
        raise Conflict("Already submitted today") from exc

    days = db.scalars(
        select(Submission.date).where(
            Submission.user_id == user.id, Submission.challenge_id == challenge_id
        )
    ).all()
    stats = compute_streaks(days, today=day)
    membership.current_streak = stats.current
    membership.max_streak = max(membership.max_streak or 0, stats.longest)
    membership.total_value = (membership.total_value or 0.0) + value
    db.flush()

    return SubmissionOutcome(
        challenge_id=challenge_id,
        day=day,
        value=value,
        current_streak=membership.current_streak,
        max_streak=membership.max_streak,
        total_value=membership.total_value,
    )


# ------------------------------------------------------------------- leaderboards


def leaderboard(
    db: Session, challenge_id: int, period: str, now_local: datetime
) -> list[dict[str, Any]]:
    if period not in LEADERBOARD_PERIODS:
        raise ValidationError(f"period must be one of: {', '.join(LEADERBOARD_PERIODS)}")
    challenge = get_active_challenge(db, challenge_id)
    today = challenge_day(now_local, challenge_window(challenge))

    total = func.sum(Submission.value).label("total_value")
    query = (
        select(User.id, User.full_name, User.username, total)
        .join(Submission, Submission.user_id == User.id)
        .where(Submission.challenge_id == challenge_id, User.is_banned.is_(False))
    )
    if period == "today":
        query = query.where(Submission.date == today)
    elif period == "weekly":
        query = query.where(Submission.date >= current_week_start(today))
    elif period == "monthly":
        query = query.where(Submission.date >= today.replace(day=1))

    rows = db.execute(
        query.group_by(User.id, User.full_name, User.username)
        .order_by(total.desc(), User.id)
        .limit(LEADERBOARD_LIMIT)
    ).all()
    standings = rank_totals({r.id: float(r.total_value) for r in rows})
    by_id = {r.id: r for r in rows}
    return [
        {
            "rank": s.rank,
            "full_name": by_id[s.user_id].full_name,
            "username": by_id[s.user_id].username,
            "total_value": s.total,
        }
        for s in standings
    ]


def streak_leaderboard(db: Session, challenge_id: int, now_local: datetime) -> list[dict[str, Any]]:
    challenge = get_active_challenge(db, challenge_id)
    today = challenge_day(now_local, challenge_window(challenge))

    last_day = (
        select(Submission.user_id, func.max(Submission.date).label("last_day"))
        .where(Submission.challenge_id == challenge_id)
        .group_by(Submission.user_id)
        .subquery()
    )
    rows = db.execute(
        select(
            User.full_name,
            User.username,
            UserChallenge.current_streak,
            UserChallenge.max_streak,
            last_day.c.last_day,
        )
        .join(UserChallenge, UserChallenge.user_id == User.id)
        .outerjoin(last_day, last_day.c.user_id == User.id)
        .where(UserChallenge.challenge_id == challenge_id, User.is_banned.is_(False))
    ).all()

    entries = [
        {
            "full_name": r.full_name,
            "username": r.username,
            "current_streak": effective_streak(r.current_streak or 0, r.last_day, today),
            "max_streak": r.max_streak or 0,
        }
        for r in rows
    ]
    entries.sort(key=lambda e: (-e["current_streak"], -e["max_streak"], e["full_name"]))
    return entries[:LEADERBOARD_LIMIT]


# ------------------------------------------------------------------ scheduled jobs


@dataclass(frozen=True)
class Reminder:
    telegram_id: int
    challenge_title: str


def pending_reminders(db: Session, now_local: datetime) -> list[Reminder]:
    """Joined, non-banned users who have not submitted for today's challenge day."""
    reminders: list[Reminder] = []
    challenges = db.scalars(select(Challenge).where(Challenge.is_active.is_(True))).all()
    for challenge in challenges:
        day = challenge_day(now_local, challenge_window(challenge))
        submitted = exists().where(
            Submission.user_id == User.id,
            Submission.challenge_id == challenge.id,
            Submission.date == day,
        )
        telegram_ids = db.scalars(
            select(User.telegram_id)
            .join(UserChallenge, UserChallenge.user_id == User.id)
            .where(
                UserChallenge.challenge_id == challenge.id,
                UserChallenge.is_joined.is_(True),
                User.is_banned.is_(False),
                ~submitted,
            )
        ).all()
        reminders.extend(Reminder(tid, challenge.title) for tid in telegram_ids)
    return reminders


@dataclass(frozen=True)
class WeeklyWinner:
    telegram_id: int
    full_name: str
    challenge_title: str
    target_unit: str
    total: float
    week_start: date


def record_weekly_results(db: Session, today: date) -> list[WeeklyWinner]:
    """Persist last week's ranking per challenge and return the winners.

    Idempotent: a challenge whose results for that week already exist is
    skipped, so a re-run (or a second bot replica) never duplicates rows.
    """
    week_start, week_end = previous_week(today)
    winners: list[WeeklyWinner] = []
    for challenge in db.scalars(select(Challenge).order_by(Challenge.id)).all():
        done = db.scalar(
            select(
                exists().where(
                    WeeklyResult.challenge_id == challenge.id,
                    WeeklyResult.week_start == week_start,
                )
            )
        )
        if done:
            continue
        rows = db.execute(
            select(Submission.user_id, func.sum(Submission.value))
            .join(User, User.id == Submission.user_id)
            .where(
                Submission.challenge_id == challenge.id,
                Submission.date >= week_start,
                Submission.date <= week_end,
                User.is_banned.is_(False),
            )
            .group_by(Submission.user_id)
        ).all()
        standings = rank_totals({uid: float(total) for uid, total in rows})
        for s in standings:
            db.add(
                WeeklyResult(
                    user_id=s.user_id,
                    challenge_id=challenge.id,
                    week_start=week_start,
                    total_value=s.total,
                    rank=s.rank,
                )
            )
            if s.rank == 1:
                user = db.get(User, s.user_id)
                if user is not None:
                    winners.append(
                        WeeklyWinner(
                            telegram_id=user.telegram_id,
                            full_name=user.full_name,
                            challenge_title=challenge.title,
                            target_unit=challenge.target_unit,
                            total=s.total,
                            week_start=week_start,
                        )
                    )
    db.flush()
    return winners


# -------------------------------------------------------------------------- admin

CHALLENGE_CODE_RE = re.compile(r"^[a-z][a-z0-9_]{0,31}$")
RESERVED_CODES = frozenset({"start", "submit", "cancel", "help"})
_CHALLENGE_FIELDS = (
    "title",
    "description",
    "code",
    "target_unit",
    "time_window_start",
    "time_window_end",
    "is_active",
)


def _str_field(data: dict, key: str, max_len: int, *, required: bool) -> str | None:
    value = data.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        if required:
            raise ValidationError(f"{key} is required")
        return None
    if not isinstance(value, str):
        raise ValidationError(f"{key} must be a string")
    value = value.strip()
    if len(value) > max_len:
        raise ValidationError(f"{key} must be at most {max_len} characters")
    return value


def validate_challenge_payload(data: Any, *, partial: bool) -> dict[str, Any]:
    """Whitelist and validate admin input for creating/updating a challenge."""
    if not isinstance(data, dict):
        raise ValidationError("JSON object expected")
    unknown = set(data) - set(_CHALLENGE_FIELDS)
    if unknown:
        raise ValidationError(f"unknown fields: {', '.join(sorted(unknown))}")

    clean: dict[str, Any] = {}
    if not partial or "title" in data:
        clean["title"] = _str_field(data, "title", 255, required=True)
    if "description" in data:
        clean["description"] = _str_field(data, "description", 1000, required=False)
    if not partial or "code" in data:
        code = _str_field(data, "code", 32, required=True)
        code = code.lower() if code else code
        if not code or not CHALLENGE_CODE_RE.match(code):
            raise ValidationError(
                "code must start with a letter and contain only a-z, 0-9 and _ (max 32)"
            )
        if code in RESERVED_CODES:
            raise ValidationError(f"code {code!r} is reserved by the bot")
        clean["code"] = code
    if "target_unit" in data:
        clean["target_unit"] = _str_field(data, "target_unit", 50, required=False) or "units"
    elif not partial:
        clean["target_unit"] = "units"
    for key in ("time_window_start", "time_window_end"):
        if key in data:
            clean[key] = _str_field(data, key, 5, required=False)
    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            raise ValidationError("is_active must be a boolean")
        clean["is_active"] = data["is_active"]
    return clean


def _check_window(start: str | None, end: str | None) -> None:
    try:
        SubmissionWindow.parse(start, end)
    except ValueError as exc:
        raise ValidationError(str(exc)) from exc


def _ensure_unique_code(db: Session, code: str, exclude_id: int | None = None) -> None:
    query = select(Challenge.id).where(Challenge.code == code)
    if exclude_id is not None:
        query = query.where(Challenge.id != exclude_id)
    if db.scalar(query) is not None:
        raise Conflict(f"challenge code {code!r} already exists")


def create_challenge(db: Session, data: Any) -> Challenge:
    clean = validate_challenge_payload(data, partial=False)
    _check_window(clean.get("time_window_start"), clean.get("time_window_end"))
    _ensure_unique_code(db, clean["code"])
    challenge = Challenge(**clean)
    db.add(challenge)
    try:
        db.flush()
    except IntegrityError as exc:
        raise Conflict("challenge code already exists") from exc
    return challenge


def update_challenge(db: Session, challenge_id: int, data: Any) -> Challenge:
    clean = validate_challenge_payload(data, partial=True)
    challenge = db.get(Challenge, challenge_id)
    if challenge is None:
        raise NotFound("Challenge not found")
    _check_window(
        clean.get("time_window_start", challenge.time_window_start),
        clean.get("time_window_end", challenge.time_window_end),
    )
    if "code" in clean:
        _ensure_unique_code(db, clean["code"], exclude_id=challenge.id)
    for key, value in clean.items():
        setattr(challenge, key, value)
    db.flush()
    return challenge


def list_all_challenges(db: Session) -> list[dict[str, Any]]:
    return [challenge_to_dict(c) for c in db.scalars(select(Challenge).order_by(Challenge.id))]


def list_users(db: Session, *, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
    users = db.scalars(select(User).order_by(User.id).limit(limit).offset(offset)).all()
    return [user_to_dict(u) for u in users]


def set_banned(db: Session, user_id: int, banned: bool) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFound("User not found")
    user.is_banned = banned
    db.flush()
    return user
