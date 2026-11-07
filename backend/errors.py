"""Domain/service exceptions mapped to HTTP status codes by the API layer."""

from __future__ import annotations


class ServiceError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(ServiceError):
    status_code = 400
    code = "validation_error"


class Unauthorized(ServiceError):
    status_code = 401
    code = "unauthorized"


class Forbidden(ServiceError):
    status_code = 403
    code = "forbidden"


class NotFound(ServiceError):
    status_code = 404
    code = "not_found"


class Conflict(ServiceError):
    status_code = 409
    code = "conflict"


class SubmissionWindowClosed(ServiceError):
    status_code = 422
    code = "window_closed"


class ServiceUnavailable(ServiceError):
    status_code = 503
    code = "service_unavailable"
