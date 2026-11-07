"""Streak computation over *local* calendar days.

A streak is the number of consecutive challenge days with a submission. The
functions here work with :class:`datetime.date` values that were already
converted to the club timezone, so they are independent of server timezone.
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

_ONE_DAY = timedelta(days=1)


@dataclass(frozen=True)
class StreakStats:
    current: int
    longest: int


def compute_streaks(days: Iterable[date], today: date) -> StreakStats:
    """Compute current and longest streak from the days a user submitted.

    ``current`` counts the run of consecutive days ending ``today`` -- or
    ending yesterday, because a streak is still alive until the user misses a
    whole day. Duplicate and future dates are ignored.
    """
    unique = sorted({d for d in days if d <= today})
    if not unique:
        return StreakStats(current=0, longest=0)

    longest = run = 1
    for prev, cur in itertools.pairwise(unique):
        run = run + 1 if cur - prev == _ONE_DAY else 1
        longest = max(longest, run)

    current = 0
    if unique[-1] >= today - _ONE_DAY:
        current = 1
        for i in range(len(unique) - 1, 0, -1):
            if unique[i] - unique[i - 1] != _ONE_DAY:
                break
            current += 1
    return StreakStats(current=current, longest=longest)


def effective_streak(stored_streak: int, last_day: date | None, today: date) -> int:
    """Return the streak to *display* given the stored value and last activity.

    The stored counter is only updated on submission, so a user who stopped
    submitting would otherwise keep showing an old streak forever.
    """
    if last_day is None or last_day < today - _ONE_DAY:
        return 0
    return stored_streak
