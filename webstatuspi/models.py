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
        content_length: Response Content-Length header value, or None if not provided.
        server_header: Response Server header value, or None if not provided.
        status_text: HTTP status reason phrase (e.g., "OK", "Not Found"), or None if not available.
        ssl_cert_issuer: SSL certificate issuer organization, or None for HTTP URLs.
        ssl_cert_subject: SSL certificate subject common name, or None for HTTP URLs.
        ssl_cert_expires_at: SSL certificate expiration timestamp, or None for HTTP URLs.
        ssl_cert_expires_in_days: Days until SSL certificate expires (negative if expired), or None.
        ssl_cert_error: Error message if SSL certificate extraction failed, or None.
    """

    url_name: str
    url: str
    status_code: int | None
    response_time_ms: int
    is_up: bool
    error_message: str | None
    checked_at: datetime
    content_length: int | None = None
    server_header: str | None = None
    status_text: str | None = None
    ssl_cert_issuer: str | None = None
    ssl_cert_subject: str | None = None
    ssl_cert_expires_at: datetime | None = None
    ssl_cert_expires_in_days: int | None = None
    ssl_cert_error: str | None = None


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
        avg_response_time_24h: Average response time in last 24 hours (ms).
        min_response_time_24h: Minimum response time in last 24 hours (ms).
        max_response_time_24h: Maximum response time in last 24 hours (ms).
        consecutive_failures: Count of consecutive failed checks from most recent.
        last_downtime: Timestamp of most recent failed check, or None if never failed.
        content_length: Most recent response Content-Length, or None if not provided.
        server_header: Most recent response Server header, or None if not provided.
        status_text: Most recent HTTP status reason phrase, or None if not available.
        p50_response_time_24h: Median (50th percentile) response time in last 24h (ms).
        p95_response_time_24h: 95th percentile response time in last 24h (ms).
        p99_response_time_24h: 99th percentile response time in last 24h (ms).
        stddev_response_time_24h: Standard deviation of response times in last 24h (ms).
        ssl_cert_issuer: SSL certificate issuer organization, or None for HTTP URLs.
        ssl_cert_subject: SSL certificate subject common name, or None for HTTP URLs.
        ssl_cert_expires_at: SSL certificate expiration timestamp, or None for HTTP URLs.
        ssl_cert_expires_in_days: Days until SSL certificate expires (negative if expired), or None.
        ssl_cert_error: Error message if SSL certificate extraction failed, or None.
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
    avg_response_time_24h: float | None = None
    min_response_time_24h: int | None = None
    max_response_time_24h: int | None = None
    consecutive_failures: int = 0
    last_downtime: datetime | None = None
    content_length: int | None = None
    server_header: str | None = None
    status_text: str | None = None
    p50_response_time_24h: int | None = None
    p95_response_time_24h: int | None = None
    p99_response_time_24h: int | None = None
    stddev_response_time_24h: float | None = None
    ssl_cert_issuer: str | None = None
    ssl_cert_subject: str | None = None
    ssl_cert_expires_at: datetime | None = None
    ssl_cert_expires_in_days: int | None = None
    ssl_cert_error: str | None = None
