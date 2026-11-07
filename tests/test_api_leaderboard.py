from tests.conftest import tma


def submit(client, cid, value, user_id):
    r = client.post(f"/api/challenges/{cid}/submit", headers=tma(user_id), json={"value": value})
    assert r.status_code == 200, r.json


def test_leaderboard_periods(client, make_challenge, clock):
    cid = make_challenge()
    clock.set(2026, 2, 27, 12, 0)  # previous month
    submit(client, cid, 100, user_id=1)
    clock.set(2026, 3, 9, 12, 0)  # Monday of the current week
    submit(client, cid, 30, user_id=2)
    clock.set(2026, 3, 10, 12, 0)
    submit(client, cid, 20, user_id=1)
    submit(client, cid, 20, user_id=3)

    def board(period):
        r = client.get(f"/api/leaderboard/?challenge_id={cid}&period={period}", headers=tma())
        assert r.status_code == 200
        return [(e["rank"], e["total_value"]) for e in r.json]

    assert board("today") == [(1, 20), (1, 20)]
    assert board("weekly") == [(1, 30), (2, 20), (2, 20)]
    assert board("monthly") == [(1, 30), (2, 20), (2, 20)]
    assert board("all") == [(1, 120), (2, 30), (3, 20)]


def test_leaderboard_validation(client, make_challenge):
    cid = make_challenge()
    assert client.get("/api/leaderboard/", headers=tma()).status_code == 400
    assert client.get("/api/leaderboard/?challenge_id=x", headers=tma()).status_code == 400
    r = client.get(f"/api/leaderboard/?challenge_id={cid}&period=yearly", headers=tma())
    assert r.status_code == 400
    assert client.get("/api/leaderboard/?challenge_id=999", headers=tma()).status_code == 404


def test_streak_leaderboard_zeroes_stale_streaks(client, make_challenge, clock):
    cid = make_challenge()
    for day in (1, 2, 3):
        clock.set(2026, 3, day, 12, 0)
        submit(client, cid, 1, user_id=1)  # 3-day streak, then stops
    for day in (8, 9, 10):
        clock.set(2026, 3, day, 12, 0)
        submit(client, cid, 1, user_id=2)
    clock.set(2026, 3, 10, 18, 0)
    r = client.get(f"/api/leaderboard/streaks?challenge_id={cid}", headers=tma())
    entries = [(e["current_streak"], e["max_streak"]) for e in r.json]
    assert entries == [(3, 3), (0, 3)]
