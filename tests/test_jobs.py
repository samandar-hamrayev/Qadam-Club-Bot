"""Scheduled-job services: reminders and weekly winners."""

from datetime import date, datetime

from backend import services
from backend.database import session_scope
from backend.models import User, WeeklyResult
from tests.conftest import TZ, tma


def submit(client, cid, value, user_id):
    r = client.post(f"/api/challenges/{cid}/submit", headers=tma(user_id), json={"value": value})
    assert r.status_code == 200, r.json


def test_pending_reminders_only_for_joined_users_without_submission(client, make_challenge, clock):
    cid = make_challenge("steps", title="Steps")
    for uid in (1, 2, 3):
        client.post(f"/api/challenges/{cid}/join", headers=tma(uid))
    client.post("/api/auth/register", headers=tma(4))  # registered, never joined
    clock.set(2026, 3, 10, 12, 0)
    submit(client, cid, 10, user_id=1)
    with session_scope() as db:
        db.query(User).filter_by(telegram_id=3).one().is_banned = True

    with session_scope() as db:
        reminders = services.pending_reminders(db, datetime(2026, 3, 10, 21, 0, tzinfo=TZ))
    assert [(r.telegram_id, r.challenge_title) for r in reminders] == [(2, "Steps")]


def test_weekly_results_rank_winners_and_are_idempotent(client, make_challenge, clock):
    cid = make_challenge("steps")
    # Week of Mon 2026-03-02 .. Sun 2026-03-08
    clock.set(2026, 3, 2, 12, 0)
    submit(client, cid, 50, user_id=1)
    submit(client, cid, 70, user_id=2)
    clock.set(2026, 3, 8, 23, 0)
    submit(client, cid, 20, user_id=1)  # user 1 ties user 2 at 70
    clock.set(2026, 3, 9, 0, 1)  # Monday: belongs to the new week
    submit(client, cid, 999, user_id=3)

    with session_scope() as db:
        winners = services.record_weekly_results(db, date(2026, 3, 9))
    assert sorted(w.telegram_id for w in winners) == [1, 2]
    assert all(w.week_start == date(2026, 3, 2) and w.total == 70 for w in winners)

    with session_scope() as db:
        assert services.record_weekly_results(db, date(2026, 3, 9)) == []
        rows = db.query(WeeklyResult).order_by(WeeklyResult.user_id).all()
        assert [(r.user_id, r.rank) for r in rows] == [(1, 1), (2, 1)]


def test_weekly_results_without_submissions(app, make_challenge):
    make_challenge()
    with session_scope() as db:
        assert services.record_weekly_results(db, date(2026, 3, 9)) == []
