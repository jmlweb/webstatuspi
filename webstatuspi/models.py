"""Data models for URL monitoring results."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CheckResult:
    """Result of a single URL check.

    Attributes:
        url_name: Short identifier for the URL (max 10 chars).
        url: Full URL that was checked.
        status_code: HTTP status code, or None if request failed.
        response_time_ms: Response time in milliseconds.
        is_up: Whether the check was successful (2xx status code).
        error_message: Error description if the check failed, None otherwise.
        checked_at: Timestamp when the check was performed.
    """

    url_name: str
    url: str
    status_code: int | None
    response_time_ms: int
    is_up: bool
    error_message: str | None
    checked_at: datetime


@dataclass(frozen=True)
class UrlStatus:
    """Current status summary for a monitored URL.

    Attributes:
        url_name: Short identifier for the URL.
        url: Full URL being monitored.
        is_up: Current status (up/down).
        last_status_code: Most recent HTTP status code.
        last_response_time_ms: Most recent response time in milliseconds.
        last_error: Most recent error message, if any.
        last_check: Timestamp of the most recent check.
        checks_24h: Total number of checks in last 24 hours.
        uptime_24h: Uptime percentage in last 24 hours (0.0-100.0).
    """

    url_name: str
    url: str
    is_up: bool
    last_status_code: int | None
    last_response_time_ms: int
    last_error: str | None
    last_check: datetime
    checks_24h: int
    uptime_24h: float
