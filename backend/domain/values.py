"""Validation of user-submitted result values."""

from __future__ import annotations

import math

MAX_SUBMISSION_VALUE = 1_000_000.0


def parse_submission_value(raw: object) -> float:
    """Coerce ``raw`` to a positive, finite float within sane bounds.

    Booleans are rejected explicitly (``True`` is an ``int`` in Python).
    Raises ``ValueError`` with a user-facing message.
    """
    if isinstance(raw, bool) or raw is None:
        raise ValueError("value must be a number")
    if isinstance(raw, str):
        raw = raw.strip().replace(",", ".")
    try:
        value = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError("value must be a number") from exc
    if not math.isfinite(value):
        raise ValueError("value must be a finite number")
    if value <= 0:
        raise ValueError("value must be greater than zero")
    if value > MAX_SUBMISSION_VALUE:
        raise ValueError(f"value must not exceed {MAX_SUBMISSION_VALUE:g}")
    return value
