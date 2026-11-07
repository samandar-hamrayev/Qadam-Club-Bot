from __future__ import annotations

from typing import Any

from flask import request

from ..errors import ValidationError


def json_body() -> dict[str, Any]:
    """Return the JSON object body or raise a 400."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ValidationError("JSON object body expected")
    return data


def int_arg(name: str, *, required: bool = True, default: int | None = None) -> int | None:
    raw = request.args.get(name)
    if raw is None or raw == "":
        if required:
            raise ValidationError(f"{name} is required")
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValidationError(f"{name} must be an integer") from exc
