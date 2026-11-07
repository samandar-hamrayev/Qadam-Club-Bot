"""Pure helpers for parsing chat input (no Telegram objects involved)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ChallengeCommand:
    code: str
    value: str | None = None


def parse_challenge_command(text: str) -> ChallengeCommand | None:
    """Parse ``/code`` or ``/code 1500`` (also ``/code@BotName 1500``).

    Returns ``None`` when ``text`` is not a command.
    """
    text = (text or "").strip()
    if not text.startswith("/"):
        return None
    parts = text[1:].split()
    if not parts:
        return None
    code = parts[0].split("@", 1)[0].lower()
    if not code:
        return None
    return ChallengeCommand(code=code, value=parts[1] if len(parts) > 1 else None)
