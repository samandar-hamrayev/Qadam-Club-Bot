"""Engine and session management shared by the API and the bot."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from .models import AdminUser, Base

logger = logging.getLogger(__name__)

SessionLocal = sessionmaker(autoflush=False, expire_on_commit=False)
_engine: Engine | None = None


def init_engine(database_url: str) -> Engine:
    """Create the global engine and bind :data:`SessionLocal` to it."""
    global _engine
    kwargs: dict = {"pool_pre_ping": True}
    if database_url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
        if database_url in {"sqlite://", "sqlite:///:memory:"}:
            # Share one in-memory database across threads (tests).
            kwargs["poolclass"] = StaticPool
    if _engine is not None:
        _engine.dispose()
    _engine = create_engine(database_url, **kwargs)
    SessionLocal.configure(bind=_engine)
    return _engine


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("database engine is not initialised; call init_engine() first")
    return _engine


def release_connections() -> None:
    """Close pooled connections, e.g. before gunicorn forks its workers.

    In-memory SQLite (tests) lives inside its single connection, so it is kept.
    """
    engine = get_engine()
    if not isinstance(engine.pool, StaticPool):
        engine.dispose()


def create_schema() -> None:
    Base.metadata.create_all(bind=get_engine())


def seed_admins(admin_ids: Iterable[int]) -> None:
    """Ensure every Telegram id from ``ADMIN_IDS`` has an admin record."""
    with session_scope() as db:
        existing = set(db.scalars(select(AdminUser.telegram_id)))
        for admin_id in admin_ids:
            if admin_id not in existing:
                db.add(AdminUser(telegram_id=admin_id, role="superadmin"))
    logger.info("admin users seeded")


def init_db(admin_ids: Iterable[int] = ()) -> None:
    create_schema()
    try:
        seed_admins(admin_ids)
    except IntegrityError:
        # Another process seeded concurrently; nothing to do.
        logger.info("admin seeding raced with another process; skipping")


def ping() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:  # pragma: no cover - depends on a broken database
        logger.exception("database ping failed")
        return False


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional scope: commit on success, roll back on any exception."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
