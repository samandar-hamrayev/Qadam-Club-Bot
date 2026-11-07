"""Submission time windows.

A challenge may restrict submissions to a daily local-time window, e.g.
``21:00-23:59``. Windows may also cross midnight (``22:00-01:00``); in that
case a submission made after midnight still belongs to the *previous*
"challenge day", so a late reader does not accidentally break their streak.

All times are wall-clock times in the configured club timezone. Both ends are
inclusive at minute precision: with an end of ``23:59`` a submission at
``23:59:59`` is accepted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def parse_hhmm(value: str) -> time:
    """Parse a strict ``HH:MM`` (24h) string into a :class:`datetime.time`."""
    if not isinstance(value, str):
        raise ValueError("time must be a string in HH:MM format")
    match = _HHMM.match(value.strip())
    if not match:
        raise ValueError(f"invalid time {value!r}, expected HH:MM")
    return time(int(match.group(1)), int(match.group(2)))


def _to_minute(t: time) -> time:
    return t.replace(second=0, microsecond=0, tzinfo=None)


@dataclass(frozen=True)
class SubmissionWindow:
    start: time
    end: time

    @classmethod
    def parse(cls, start: str | None, end: str | None) -> SubmissionWindow | None:
        """Build a window from stored strings; ``None`` when the challenge is open all day.

        Raises ``ValueError`` if only one bound is set or a bound is malformed.
        """
        if not start and not end:
            return None
        if not start or not end:
            raise ValueError("both time_window_start and time_window_end must be set")
        return cls(parse_hhmm(start), parse_hhmm(end))

    @property
    def wraps_midnight(self) -> bool:
        return self.start > self.end

    def contains(self, moment: time) -> bool:
        t = _to_minute(moment)
        if self.wraps_midnight:
            return t >= self.start or t <= self.end
        return self.start <= t <= self.end

    def __str__(self) -> str:
        return f"{self.start:%H:%M}-{self.end:%H:%M}"


def is_submission_open(window: SubmissionWindow | None, now_local: datetime) -> bool:
    """Return whether a submission at ``now_local`` (club timezone) is allowed."""
    return window is None or window.contains(now_local.time())


def challenge_day(now_local: datetime, window: SubmissionWindow | None) -> date:
    """Return the logical day a submission at ``now_local`` counts towards.

    For windows crossing midnight, the after-midnight part belongs to the
    previous calendar day.
    """
    if window is not None and window.wraps_midnight and _to_minute(now_local.time()) <= window.end:
        return now_local.date() - timedelta(days=1)
    return now_local.date()
