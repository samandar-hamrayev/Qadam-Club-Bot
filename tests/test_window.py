from datetime import date, datetime, time
from zoneinfo import ZoneInfo

import pytest

from backend.domain.window import (
    SubmissionWindow,
    challenge_day,
    is_submission_open,
    parse_hhmm,
)

TZ = ZoneInfo("Asia/Tashkent")


def at(h: int, m: int, s: int = 0, day: int = 10) -> datetime:
    return datetime(2026, 3, day, h, m, s, tzinfo=TZ)


@pytest.mark.parametrize("raw", ["24:00", "9:00", "12:60", "ab:cd", "", "12:00:00", None, 1200])
def test_parse_hhmm_rejects_garbage(raw):
    with pytest.raises(ValueError):
        parse_hhmm(raw)


def test_parse_hhmm_accepts_valid():
    assert parse_hhmm("00:00") == time(0, 0)
    assert parse_hhmm(" 23:59 ") == time(23, 59)


def test_window_parse_requires_both_bounds():
    assert SubmissionWindow.parse(None, None) is None
    assert SubmissionWindow.parse("", "") is None
    with pytest.raises(ValueError):
        SubmissionWindow.parse("21:00", None)


EVENING = SubmissionWindow(time(21, 0), time(23, 59))


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (at(20, 59, 59), False),
        (at(21, 0, 0), True),
        (at(22, 30), True),
        (at(23, 59, 0), True),
        (at(23, 59, 59), True),  # end minute is inclusive
        (at(0, 0, 0), False),  # just after midnight
        (at(12, 0), False),
    ],
)
def test_evening_window(moment, expected):
    assert is_submission_open(EVENING, moment) is expected


def test_no_window_means_always_open():
    assert is_submission_open(None, at(3, 0))
    assert challenge_day(at(0, 30), None) == date(2026, 3, 10)


OVERNIGHT = SubmissionWindow(time(22, 0), time(1, 0))


@pytest.mark.parametrize(
    ("moment", "expected"),
    [
        (at(21, 59), False),
        (at(22, 0), True),
        (at(23, 59, 59), True),
        (at(0, 0), True),
        (at(1, 0, 59), True),
        (at(1, 1), False),
    ],
)
def test_window_crossing_midnight(moment, expected):
    assert OVERNIGHT.wraps_midnight
    assert OVERNIGHT.contains(moment.time()) is expected


def test_after_midnight_counts_towards_previous_day():
    assert challenge_day(at(23, 30, day=10), OVERNIGHT) == date(2026, 3, 10)
    assert challenge_day(at(0, 30, day=11), OVERNIGHT) == date(2026, 3, 10)
    assert challenge_day(at(1, 1, day=11), OVERNIGHT) == date(2026, 3, 11)


def test_str():
    assert str(EVENING) == "21:00-23:59"
