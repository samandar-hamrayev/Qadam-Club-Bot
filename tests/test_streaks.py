from datetime import date, timedelta

from backend.domain.streaks import compute_streaks, effective_streak

D = date(2026, 3, 10)


def days(*offsets: int) -> list[date]:
    return [D + timedelta(days=o) for o in offsets]


def test_no_submissions():
    stats = compute_streaks([], D)
    assert (stats.current, stats.longest) == (0, 0)


def test_consecutive_days_ending_today():
    stats = compute_streaks(days(-3, -2, -1, 0), D)
    assert (stats.current, stats.longest) == (4, 4)


def test_streak_alive_until_a_full_day_is_missed():
    # Submitted up to yesterday, not yet today: streak is still 3.
    assert compute_streaks(days(-3, -2, -1), D).current == 3


def test_gap_resets_current_but_keeps_longest():
    stats = compute_streaks(days(-10, -9, -8, -7, -2, -1, 0), D)
    assert stats.current == 3
    assert stats.longest == 4


def test_missed_yesterday_breaks_streak():
    stats = compute_streaks(days(-5, -4, -3, -2), D)
    assert stats.current == 0
    assert stats.longest == 4


def test_duplicates_and_future_dates_are_ignored():
    stats = compute_streaks(days(-1, -1, 0, 0, 5), D)
    assert (stats.current, stats.longest) == (2, 2)


def test_month_and_year_boundaries():
    dec = [date(2025, 12, 30), date(2025, 12, 31), date(2026, 1, 1)]
    assert compute_streaks(dec, date(2026, 1, 1)).current == 3
    feb = [date(2028, 2, 28), date(2028, 2, 29), date(2028, 3, 1)]  # leap year
    assert compute_streaks(feb, date(2028, 3, 1)).current == 3


def test_effective_streak_hides_stale_values():
    assert effective_streak(5, D, D) == 5
    assert effective_streak(5, D - timedelta(days=1), D) == 5
    assert effective_streak(5, D - timedelta(days=2), D) == 0
    assert effective_streak(5, None, D) == 0
