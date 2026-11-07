from datetime import date

from backend.domain.ranking import current_week_start, previous_week, rank_totals, select_winners


def test_previous_week_from_any_weekday():
    # 2026-03-16 is a Monday.
    assert previous_week(date(2026, 3, 16)) == (date(2026, 3, 9), date(2026, 3, 15))
    assert previous_week(date(2026, 3, 22)) == (date(2026, 3, 9), date(2026, 3, 15))
    assert previous_week(date(2026, 1, 1)) == (date(2025, 12, 22), date(2025, 12, 28))


def test_current_week_start():
    assert current_week_start(date(2026, 3, 18)) == date(2026, 3, 16)


def test_rank_totals_orders_and_shares_ranks_on_ties():
    standings = rank_totals({1: 50, 2: 80, 3: 80, 4: 10})
    assert [(s.user_id, s.rank) for s in standings] == [(2, 1), (3, 1), (1, 3), (4, 4)]


def test_zero_totals_are_excluded():
    assert rank_totals({1: 0, 2: -3}) == []


def test_select_winners_single_and_tie():
    assert [w.user_id for w in select_winners({1: 5, 2: 9})] == [2]
    assert [w.user_id for w in select_winners({1: 9, 2: 9, 3: 1})] == [1, 2]
    assert select_winners({}) == []
