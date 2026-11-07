"""Weekly ranking and winner selection."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class Standing:
    user_id: int
    total: float
    rank: int


def previous_week(today: date) -> tuple[date, date]:
    """Return (monday, sunday) of the ISO week before the one containing ``today``."""
    this_monday = today - timedelta(days=today.weekday())
    last_monday = this_monday - timedelta(days=7)
    return last_monday, last_monday + timedelta(days=6)


def current_week_start(today: date) -> date:
    return today - timedelta(days=today.weekday())


def rank_totals(totals: Mapping[int, float]) -> list[Standing]:
    """Rank users by total, highest first, using standard competition ranking.

    Equal totals share a rank ("1224" ranking); ties are listed by user id so
    the output is deterministic. Users with a non-positive total are excluded.
    """
    ordered = sorted(
        ((uid, total) for uid, total in totals.items() if total > 0),
        key=lambda item: (-item[1], item[0]),
    )
    standings: list[Standing] = []
    for position, (uid, total) in enumerate(ordered, start=1):
        rank = standings[-1].rank if standings and standings[-1].total == total else position
        standings.append(Standing(user_id=uid, total=total, rank=rank))
    return standings


def select_winners(totals: Mapping[int, float]) -> list[Standing]:
    """Return every user tied for first place (empty if nobody scored)."""
    return [s for s in rank_totals(totals) if s.rank == 1]
