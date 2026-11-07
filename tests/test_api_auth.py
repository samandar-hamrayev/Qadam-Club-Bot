import time

import pytest

from backend.app import create_app
from tests.conftest import ADMIN_HEADERS, ADMIN_TG_ID, make_init_data, tma

TMA_ENDPOINTS = [
    ("post", "/api/auth/register"),
    ("get", "/api/challenges/"),
    ("post", "/api/challenges/1/join"),
    ("post", "/api/challenges/1/submit"),
    ("get", "/api/leaderboard/?challenge_id=1"),
    ("get", "/api/leaderboard/streaks?challenge_id=1"),
]


@pytest.mark.parametrize(("method", "url"), TMA_ENDPOINTS)
def test_tma_endpoints_require_init_data(client, method, url):
    response = getattr(client, method)(url, json={"value": 1})
    assert response.status_code == 401
    assert response.json["code"] == "unauthorized"


@pytest.mark.parametrize(("method", "url"), TMA_ENDPOINTS)
def test_tma_endpoints_reject_forged_init_data(client, method, url):
    headers = {"Authorization": f"tma {make_init_data(1, bot_token='999:attacker')}"}
    response = getattr(client, method)(url, headers=headers, json={"value": 1})
    assert response.status_code == 401


def test_expired_init_data_is_rejected(client):
    stale = int(time.time()) - 2 * 86400
    response = client.post("/api/auth/register", headers=tma(auth_date=stale))
    assert response.status_code == 401
    assert "expired" in response.json["error"]


def test_client_supplied_telegram_id_is_ignored(client):
    """The old API trusted ``telegram_id`` from the body; now only initData counts."""
    response = client.post("/api/auth/register", headers=tma(42), json={"telegram_id": ADMIN_TG_ID})
    assert response.status_code == 200
    assert response.json["user"]["telegram_id"] == 42
    assert response.json["user"]["is_admin"] is False


def test_register_upserts_profile(client):
    first = client.post("/api/auth/register", headers=tma(7, first_name="Old")).json["user"]
    second = client.post("/api/auth/register", headers=tma(7, first_name="New")).json["user"]
    assert first["id"] == second["id"]
    assert second["full_name"] == "New"


def test_register_marks_admins(client):
    response = client.post("/api/auth/register", headers=tma(ADMIN_TG_ID))
    assert response.json["user"]["is_admin"] is True


def test_missing_bot_token_returns_503(settings, clock):
    from dataclasses import replace

    app = create_app(replace(settings, bot_token=None), clock=clock)
    response = app.test_client().post("/api/auth/register", headers=tma())
    assert response.status_code == 503


def test_health_and_index(client):
    assert client.get("/healthz").json == {"status": "ok", "database": "ok"}
    assert client.get("/").json["status"] == "ok"


def test_static_pages_and_api_docs(client):
    assert client.get("/tma").status_code == 200
    assert client.get("/admin-panel").status_code == 200
    spec = client.get("/apispec_1.json").json
    assert "/api/challenges/{challenge_id}/submit" in spec["paths"]


def test_security_headers(client):
    response = client.get("/api/challenges/")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Cache-Control"] == "no-store"


def test_unknown_route_returns_json_404(client):
    response = client.get("/api/nope", headers=ADMIN_HEADERS)
    assert response.status_code == 404
    assert response.json["code"] == "not_found"
