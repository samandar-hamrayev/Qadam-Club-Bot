from backend.database import session_scope
from backend.models import Submission, User, UserChallenge
from tests.conftest import tma


def submit(client, challenge_id, value=10, user_id=42):
    return client.post(
        f"/api/challenges/{challenge_id}/submit", headers=tma(user_id), json={"value": value}
    )


def test_list_challenges_with_membership(client, make_challenge):
    steps = make_challenge("steps")
    make_challenge("book")
    make_challenge("hidden", is_active=False)

    response = client.get("/api/challenges/", headers=tma())
    assert response.status_code == 200
    assert [c["code"] for c in response.json] == ["steps", "book"]
    assert not any(c["is_joined"] for c in response.json)

    assert client.post(f"/api/challenges/{steps}/join", headers=tma()).status_code == 200
    joined = {c["code"]: c["is_joined"] for c in client.get("/api/challenges/", headers=tma()).json}
    assert joined == {"steps": True, "book": False}


def test_join_unknown_or_inactive_challenge(client, make_challenge):
    inactive = make_challenge("old", is_active=False)
    assert client.post("/api/challenges/999/join", headers=tma()).status_code == 404
    assert client.post(f"/api/challenges/{inactive}/join", headers=tma()).status_code == 404


def test_join_twice_is_idempotent(client, make_challenge):
    cid = make_challenge()
    client.post(f"/api/challenges/{cid}/join", headers=tma())
    client.post(f"/api/challenges/{cid}/join", headers=tma())
    with session_scope() as db:
        assert db.query(UserChallenge).count() == 1


def test_submission_happy_path(client, make_challenge, clock):
    cid = make_challenge()
    clock.set(2026, 3, 10, 12, 0)
    response = submit(client, cid, value=5000)
    assert response.status_code == 200
    body = response.json
    assert body["current_streak"] == 1
    assert body["max_streak"] == 1
    assert body["total_value"] == 5000
    assert body["date"] == "2026-03-10"
    with session_scope() as db:
        assert db.query(Submission).one().value == 5000


def test_duplicate_submission_same_day_is_rejected(client, make_challenge, clock):
    cid = make_challenge()
    clock.set(2026, 3, 10, 9, 0)
    assert submit(client, cid).status_code == 200
    clock.set(2026, 3, 10, 23, 0)
    response = submit(client, cid)
    assert response.status_code == 409
    assert response.json["code"] == "conflict"
    with session_scope() as db:
        assert db.query(Submission).count() == 1


def test_streak_grows_on_consecutive_local_days_and_resets_after_gap(client, make_challenge, clock):
    cid = make_challenge()
    for day, expected in [(10, 1), (11, 2), (12, 3), (14, 1), (15, 2)]:
        clock.set(2026, 3, day, 12, 0)
        response = submit(client, cid)
        assert response.json["current_streak"] == expected, day
    assert response.json["max_streak"] == 3
    assert response.json["total_value"] == 50


def test_streak_uses_local_date_not_utc(client, make_challenge, clock):
    """23:30 and 00:30 Tashkent are the same UTC day but different local days."""
    cid = make_challenge()
    clock.set(2026, 3, 10, 23, 30)  # 18:30 UTC
    assert submit(client, cid).status_code == 200
    clock.set(2026, 3, 11, 0, 30)  # 19:30 UTC, same UTC date
    response = submit(client, cid)
    assert response.status_code == 200
    assert response.json["current_streak"] == 2
    assert response.json["date"] == "2026-03-11"


def test_time_window_is_enforced_for_every_challenge(client, make_challenge, clock):
    cid = make_challenge("book", start="21:00", end="23:59")
    clock.set(2026, 3, 10, 20, 59)
    response = submit(client, cid)
    assert response.status_code == 422
    assert "21:00-23:59" in response.json["error"]

    clock.set(2026, 3, 10, 23, 59)
    assert submit(client, cid).status_code == 200


def test_overnight_window_keeps_streak(client, make_challenge, clock):
    cid = make_challenge("night", start="22:00", end="01:00")
    clock.set(2026, 3, 10, 22, 15)
    assert submit(client, cid).json["date"] == "2026-03-10"
    clock.set(2026, 3, 12, 0, 45)  # after midnight -> counts for the 11th
    response = submit(client, cid)
    assert response.json["date"] == "2026-03-11"
    assert response.json["current_streak"] == 2


def test_invalid_values_are_rejected(client, make_challenge):
    cid = make_challenge()
    for bad in ["abc", -5, 0, None, True, 10**9]:
        response = submit(client, cid, value=bad)
        assert response.status_code == 400, bad
    assert (
        client.post(f"/api/challenges/{cid}/submit", headers=tma(), data="nope").status_code == 400
    )


def test_submit_to_unknown_challenge(client):
    assert submit(client, 12345).status_code == 404


def test_banned_user_cannot_join_or_submit(client, make_challenge):
    cid = make_challenge()
    client.post("/api/auth/register", headers=tma(42))
    with session_scope() as db:
        db.query(User).filter_by(telegram_id=42).one().is_banned = True
    assert submit(client, cid).status_code == 403
    assert client.post(f"/api/challenges/{cid}/join", headers=tma()).status_code == 403


def test_submission_auto_joins(client, make_challenge):
    cid = make_challenge()
    submit(client, cid)
    challenges = client.get("/api/challenges/", headers=tma()).json
    assert challenges[0]["is_joined"] is True
