import pytest

from backend.database import session_scope
from backend.models import Challenge
from tests.conftest import ADMIN_HEADERS, ADMIN_TG_ID, tma

VALID = {
    "title": "Book Challenge",
    "code": "book",
    "target_unit": "pages",
    "time_window_start": "21:00",
    "time_window_end": "23:59",
}


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", "/api/admin/challenges"),
        ("post", "/api/admin/challenges"),
        ("patch", "/api/admin/challenges/1"),
        ("get", "/api/admin/users"),
        ("post", "/api/admin/users/1/ban"),
        ("post", "/api/admin/users/1/unban"),
    ],
)
def test_admin_endpoints_are_protected(client, method, url):
    call = getattr(client, method)
    assert call(url, json=VALID).status_code == 401
    wrong = {"Authorization": "Bearer " + "x" * 40}
    assert call(url, headers=wrong, json=VALID).status_code == 401
    # The legacy "admin_id in the body" trick must not work any more.
    assert call(url, json={**VALID, "admin_id": ADMIN_TG_ID}).status_code == 401
    # A regular Mini App user is authenticated but not authorised.
    assert call(url, headers=tma(42), json=VALID).status_code == 403


def test_admin_token_unset_disables_bearer(settings, clock):
    from dataclasses import replace

    from backend.app import create_app

    app = create_app(replace(settings, admin_api_token=None), clock=clock)
    r = app.test_client().get("/api/admin/users", headers=ADMIN_HEADERS)
    assert r.status_code == 401


def test_admin_via_telegram_init_data(client):
    response = client.get("/api/admin/users", headers=tma(ADMIN_TG_ID))
    assert response.status_code == 200


def test_create_and_list_challenge(client):
    response = client.post("/api/admin/challenges", headers=ADMIN_HEADERS, json=VALID)
    assert response.status_code == 201
    created = response.json["challenge"]
    assert created["code"] == "book"
    assert created["time_window_start"] == "21:00"

    listing = client.get("/api/admin/challenges", headers=ADMIN_HEADERS).json
    assert [c["code"] for c in listing] == ["book"]

    duplicate = client.post("/api/admin/challenges", headers=ADMIN_HEADERS, json=VALID)
    assert duplicate.status_code == 409


@pytest.mark.parametrize(
    "patch",
    [
        {"title": ""},
        {"code": "Bad Code!"},
        {"code": "start"},
        {"time_window_start": "25:00"},
        {"time_window_end": None},
        {"admin_id": 1},
        {"is_active": "yes"},
        {"title": "x" * 300},
        {"description": 5},
    ],
)
def test_create_challenge_validation(client, patch):
    response = client.post("/api/admin/challenges", headers=ADMIN_HEADERS, json={**VALID, **patch})
    assert response.status_code == 400, response.json


def test_create_requires_json_object(client):
    r = client.post("/api/admin/challenges", headers=ADMIN_HEADERS, json=["x"])
    assert r.status_code == 400


def test_update_challenge_whitelists_fields(client, make_challenge):
    cid = make_challenge("steps")
    other = make_challenge("book")
    url = f"/api/admin/challenges/{cid}"

    r = client.patch(url, headers=ADMIN_HEADERS, json={"title": "Walk", "is_active": False})
    assert r.status_code == 200
    assert r.json["challenge"]["title"] == "Walk"
    assert r.json["challenge"]["is_active"] is False

    # Mass assignment of internal columns is refused.
    assert client.patch(url, headers=ADMIN_HEADERS, json={"id": other}).status_code == 400
    assert client.patch(url, headers=ADMIN_HEADERS, json={"created_at": "x"}).status_code == 400
    # A window needs both ends.
    assert (
        client.patch(url, headers=ADMIN_HEADERS, json={"time_window_start": "21:00"}).status_code
        == 400
    )
    # Code must stay unique.
    assert client.patch(url, headers=ADMIN_HEADERS, json={"code": "book"}).status_code == 409
    assert (
        client.patch("/api/admin/challenges/999", headers=ADMIN_HEADERS, json={}).status_code == 404
    )
    with session_scope() as db:
        assert db.get(Challenge, cid).id == cid


def test_ban_and_unban(client, make_challenge):
    client.post("/api/auth/register", headers=tma(42))
    users = client.get("/api/admin/users?limit=10", headers=ADMIN_HEADERS).json
    uid = next(u["id"] for u in users if u["telegram_id"] == 42)

    r = client.post(f"/api/admin/users/{uid}/ban", headers=ADMIN_HEADERS)
    assert r.json["user"]["is_banned"] is True
    cid = make_challenge()
    blocked = client.post(f"/api/challenges/{cid}/submit", headers=tma(42), json={"value": 1})
    assert blocked.status_code == 403

    r = client.post(f"/api/admin/users/{uid}/unban", headers=ADMIN_HEADERS)
    assert r.json["user"]["is_banned"] is False
    assert client.post("/api/admin/users/999/ban", headers=ADMIN_HEADERS).status_code == 404


def test_users_pagination_validation(client):
    r = client.get("/api/admin/users?limit=abc", headers=ADMIN_HEADERS)
    assert r.status_code == 400
