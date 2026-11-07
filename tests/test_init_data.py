import time
from urllib.parse import parse_qsl, urlencode

import pytest

from backend.telegram_init_data import (
    InitDataError,
    InitDataExpiredError,
    InitDataSignatureError,
    validate_init_data,
)
from tests.conftest import BOT_TOKEN, make_init_data


def test_valid_init_data_returns_verified_user():
    result = validate_init_data(make_init_data(42, "Ali", username="ali"), BOT_TOKEN)
    assert result.user.id == 42
    assert result.user.first_name == "Ali"
    assert result.user.username == "ali"
    assert result.user.full_name == "Ali"
    assert result.query_id == "AAH-test"


def test_extra_fields_are_part_of_the_signature():
    data = make_init_data(extra={"signature": "abc", "chat_type": "private"})
    assert validate_init_data(data, BOT_TOKEN).user.id == 42


def _tamper(init_data: str, key: str, value: str) -> str:
    fields = dict(parse_qsl(init_data))
    fields[key] = value
    return urlencode(fields)


def test_tampered_user_is_rejected():
    forged = _tamper(make_init_data(42), "user", '{"id":1,"first_name":"Admin"}')
    with pytest.raises(InitDataSignatureError):
        validate_init_data(forged, BOT_TOKEN)


def test_tampered_hash_is_rejected():
    forged = _tamper(make_init_data(42), "hash", "0" * 64)
    with pytest.raises(InitDataSignatureError):
        validate_init_data(forged, BOT_TOKEN)


def test_missing_hash_is_rejected():
    fields = dict(parse_qsl(make_init_data(42)))
    fields.pop("hash")
    with pytest.raises(InitDataSignatureError):
        validate_init_data(urlencode(fields), BOT_TOKEN)


def test_signature_from_another_bot_is_rejected():
    data = make_init_data(42, bot_token="654321:OTHER-BOT")
    with pytest.raises(InitDataSignatureError):
        validate_init_data(data, BOT_TOKEN)


def test_expired_init_data_is_rejected():
    old = int(time.time()) - 2 * 3600
    with pytest.raises(InitDataExpiredError):
        validate_init_data(make_init_data(auth_date=old), BOT_TOKEN, max_age_seconds=3600)


def test_freshness_is_checked_against_injected_now():
    data = make_init_data(auth_date=1_000_000)
    assert validate_init_data(data, BOT_TOKEN, max_age_seconds=60, now=1_000_030).user.id == 42
    with pytest.raises(InitDataExpiredError):
        validate_init_data(data, BOT_TOKEN, max_age_seconds=60, now=1_000_061)


def test_auth_date_in_the_future_is_rejected():
    future = int(time.time()) + 3600
    with pytest.raises(InitDataError):
        validate_init_data(make_init_data(auth_date=future), BOT_TOKEN)


@pytest.mark.parametrize(
    "raw",
    ["", "not a query string", "a=1&a=2", "x" * 9000],
)
def test_malformed_input_is_rejected(raw):
    with pytest.raises(InitDataError):
        validate_init_data(raw, BOT_TOKEN)


def test_missing_bot_token_is_an_error():
    with pytest.raises(InitDataError):
        validate_init_data(make_init_data(), "")


@pytest.mark.parametrize(
    "user_json",
    ["not-json", "[]", '{"first_name":"NoId"}', '{"id":"42"}', '{"id":true}', '{"id":-5}'],
)
def test_invalid_user_payload_is_rejected(user_json):
    from backend.telegram_init_data import compute_hash

    fields = {"auth_date": str(int(time.time())), "user": user_json}
    fields["hash"] = compute_hash(fields, BOT_TOKEN)
    with pytest.raises(InitDataError):
        validate_init_data(urlencode(fields), BOT_TOKEN)


def test_missing_auth_date_is_rejected():
    from backend.telegram_init_data import compute_hash

    fields = {"user": '{"id":1,"first_name":"A"}'}
    fields["hash"] = compute_hash(fields, BOT_TOKEN)
    with pytest.raises(InitDataError):
        validate_init_data(urlencode(fields), BOT_TOKEN)
