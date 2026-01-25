"""SQLite database operations for URL check persistence."""

import sqlite3
import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .models import CheckResult, UrlStatus


class DatabaseError(Exception):
    """Raised when a database operation fails."""

    pass


# Global lock for thread-safe database access.
# SQLite allows concurrent reads but only one writer at a time.
# This lock ensures safe access from multiple threads (monitor, API handlers).
_db_lock = threading.Lock()


# =============================================================================
# STATUS CACHE (Stale-While-Revalidate)
# =============================================================================
# Caches get_latest_status() results to avoid expensive queries on every request.
# On Raspberry Pi, the complex SQL with 7 CTEs can take 6-11 seconds.
#
# Strategy: Stale-While-Revalidate
# - Fresh (< 30s): Return cached data immediately
# - Stale (30s-300s): Return cached data immediately, revalidate in background
# - Expired (> 300s): Block and fetch fresh data
#
# This ensures NO user ever waits for the slow query after the first request.

DEFAULT_FRESH_SECONDS = 30  # Data considered "fresh" for 30 seconds
DEFAULT_STALE_SECONDS = 300  # Data usable (stale) for up to 5 minutes


class _StatusCache:
    """Thread-safe cache with stale-while-revalidate strategy."""

    def __init__(
        self,
        fresh_seconds: int = DEFAULT_FRESH_SECONDS,
        stale_seconds: int = DEFAULT_STALE_SECONDS,
    ):
        self._lock = threading.Lock()
        self._fresh_seconds = fresh_seconds
        self._stale_seconds = stale_seconds
        self._cached_at: float = 0
        self._cached_result: list[UrlStatus] | None = None
        self._revalidating = False

    def get(self) -> tuple[list[UrlStatus] | None, bool]:
        """Get cached result and whether revalidation is needed.

        Returns:
            Tuple of (cached_result, needs_revalidation).
            - If fresh: (data, False)
            - If stale: (data, True) - caller should revalidate in background
            - If expired/empty: (None, False) - caller must fetch synchronously
        """
        with self._lock:
            if self._cached_result is None:
                return None, False

            age = time.monotonic() - self._cached_at

            # Fresh: return data, no revalidation needed
            if age <= self._fresh_seconds:
                return self._cached_result, False

            # Stale: return data, but signal revalidation needed
            if age <= self._stale_seconds:
                # Only signal revalidation if not already in progress
                needs_revalidation = not self._revalidating
                return self._cached_result, needs_revalidation

            # Expired: data too old to use
            return None, False

    def set(self, result: list[UrlStatus]) -> None:
        """Cache a new result."""
        with self._lock:
            self._cached_result = result
            self._cached_at = time.monotonic()
            self._revalidating = False

    def mark_revalidating(self) -> bool:
        """Mark that revalidation is in progress. Returns False if already revalidating."""
        with self._lock:
            if self._revalidating:
                return False
            self._revalidating = True
            return True

    def invalidate(self) -> None:
        """Invalidate freshness (called when new data is inserted).

        Note: We only reset the timestamp to trigger revalidation on next request,
        but keep the cached data available for stale-while-revalidate.
        """
        with self._lock:
            # Set age to stale (not expired) so data is still usable
            # but will trigger background revalidation
            if self._cached_result is not None:
                self._cached_at = time.monotonic() - self._fresh_seconds - 1


_status_cache = _StatusCache()


# =============================================================================
# HISTORY CACHE (Per-URL with TTL)
# =============================================================================
# Caches get_history() results per URL to avoid slow queries on modal open.
# Uses shorter TTL than status cache since history is typically accessed once.
#
# Strategy: Simple TTL-based cache
# - Fresh (< 30s): Return cached data immediately
# - Expired (> 30s): Fetch fresh data (but this rarely happens as modal is
#   typically closed before expiration)

HISTORY_CACHE_TTL_SECONDS = 30


class _HistoryCache:
    """Thread-safe per-URL history cache with TTL."""

    def __init__(self, ttl_seconds: int = HISTORY_CACHE_TTL_SECONDS):
        self._lock = threading.Lock()
        self._ttl_seconds = ttl_seconds
        self._cache: dict[str, tuple[float, list]] = {}  # url_name -> (timestamp, results)

    def get(self, url_name: str) -> list | None:
        """Get cached history for URL if not expired.

        Returns:
            Cached history list if fresh, None if expired or not cached.
        """
        with self._lock:
            if url_name not in self._cache:
                return None

            cached_at, results = self._cache[url_name]
            age = time.monotonic() - cached_at

            if age <= self._ttl_seconds:
                return results

            # Expired - remove from cache
            del self._cache[url_name]
            return None

    def set(self, url_name: str, results: list) -> None:
        """Cache history results for URL."""
        with self._lock:
            self._cache[url_name] = (time.monotonic(), results)

    def invalidate(self, url_name: str | None = None) -> None:
        """Invalidate cache for a specific URL or all URLs.

        Args:
            url_name: Specific URL to invalidate, or None to invalidate all.
        """
        with self._lock:
            if url_name is None:
                self._cache.clear()
            elif url_name in self._cache:
                del self._cache[url_name]


_history_cache = _HistoryCache()


def init_db(db_path: str) -> sqlite3.Connection:
    """Initialize the database and create tables if they don't exist.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        Database connection with WAL mode enabled.

    Raises:
        DatabaseError: If database initialization fails.
    """
    try:
        parent_dir = Path(db_path).parent
        if not parent_dir.exists():
            parent_dir.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row

        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url_name TEXT NOT NULL,
                url TEXT NOT NULL,
                status_code INTEGER,
                response_time_ms INTEGER NOT NULL,
                is_up INTEGER NOT NULL,
                error_message TEXT,
                checked_at TEXT NOT NULL,
                content_length INTEGER,
                server_header TEXT,
                status_text TEXT,
                ssl_cert_issuer TEXT,
                ssl_cert_subject TEXT,
                ssl_cert_expires_at TEXT,
                ssl_cert_expires_in_days INTEGER,
                ssl_cert_error TEXT
            )
        """)

        # Migrations: add columns if they don't exist (for existing databases)
        cursor = conn.execute("PRAGMA table_info(checks)")
        columns = {row[1] for row in cursor.fetchall()}
        if "content_length" not in columns:
            conn.execute("ALTER TABLE checks ADD COLUMN content_length INTEGER")
        if "server_header" not in columns:
            conn.execute("ALTER TABLE checks ADD COLUMN server_header TEXT")
        if "status_text" not in columns:
            conn.execute("ALTER TABLE checks ADD COLUMN status_text TEXT")
        # SSL certificate monitoring columns
        if "ssl_cert_issuer" not in columns:
            conn.execute("ALTER TABLE checks ADD COLUMN ssl_cert_issuer TEXT")
        if "ssl_cert_subject" not in columns:
            conn.execute("ALTER TABLE checks ADD COLUMN ssl_cert_subject TEXT")
        if "ssl_cert_expires_at" not in columns:
            conn.execute("ALTER TABLE checks ADD COLUMN ssl_cert_expires_at TEXT")
        if "ssl_cert_expires_in_days" not in columns:
            conn.execute("ALTER TABLE checks ADD COLUMN ssl_cert_expires_in_days INTEGER")
        if "ssl_cert_error" not in columns:
            conn.execute("ALTER TABLE checks ADD COLUMN ssl_cert_error TEXT")
        # TTFB (Time to First Byte) metric
        if "ttfb_ms" not in columns:
            conn.execute("ALTER TABLE checks ADD COLUMN ttfb_ms INTEGER")

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_checks_url_name
            ON checks(url_name)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_checks_checked_at
            ON checks(checked_at)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_checks_url_name_checked_at
            ON checks(url_name, checked_at)
        """)

        # Metadata table for tracking maintenance operations (e.g., last VACUUM)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        conn.commit()
        return conn

    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to initialize database: {e}")
    except OSError as e:
        raise DatabaseError(f"Failed to create database directory: {e}")


def insert_check(conn: sqlite3.Connection, result: CheckResult) -> None:
    """Insert a new check result into the database.

    Thread-safe: acquires global lock before database access.

    Args:
        conn: Database connection.
        result: Check result to insert.

    Raises:
        DatabaseError: If the insert fails.
    """
    try:
        with _db_lock:
            conn.execute(
                """
                INSERT INTO checks
                (url_name, url, status_code, response_time_ms, is_up, error_message, checked_at,
                 content_length, server_header, status_text,
                 ssl_cert_issuer, ssl_cert_subject, ssl_cert_expires_at, ssl_cert_expires_in_days, ssl_cert_error,
                 ttfb_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.url_name,
                    result.url,
                    result.status_code,
                    result.response_time_ms,
                    1 if result.is_up else 0,
                    result.error_message,
                    result.checked_at.isoformat(),
                    result.content_length,
                    result.server_header,
                    result.status_text,
                    result.ssl_cert_issuer,
                    result.ssl_cert_subject,
                    result.ssl_cert_expires_at.isoformat() if result.ssl_cert_expires_at else None,
                    result.ssl_cert_expires_in_days,
                    result.ssl_cert_error,
                    result.ttfb_ms,
                ),
            )
            conn.commit()
            # Invalidate caches since data has changed
            _status_cache.invalidate()
            _history_cache.invalidate(result.url_name)
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to insert check result: {e}")


def _fetch_latest_status_from_db(conn: sqlite3.Connection) -> list[UrlStatus]:
    """Execute the expensive status query against the database.

    Internal function - use get_latest_status() which handles caching.
    Thread-safe: acquires global lock before database access.

    Args:
        conn: Database connection.

    Returns:
        List of UrlStatus objects, one per unique URL.

    Raises:
        DatabaseError: If the query fails.
    """
    try:
        since_24h = (datetime.now(UTC) - timedelta(hours=24)).isoformat()

        rows = conn.execute(
            """
            WITH latest_checks AS (
                SELECT
                        url_name,
                        url,
                        status_code,
                        response_time_ms,
                        is_up,
                        error_message,
                        checked_at,
                        content_length,
                        server_header,
                        status_text,
                        ssl_cert_issuer,
                        ssl_cert_subject,
                        ssl_cert_expires_at,
                        ssl_cert_expires_in_days,
                        ssl_cert_error,
                        ROW_NUMBER() OVER (PARTITION BY url_name ORDER BY checked_at DESC) as rn
                    FROM checks
                ),
                stats_24h AS (
                    SELECT
                        url_name,
                        COUNT(*) as total_checks,
                        SUM(is_up) as up_checks,
                        AVG(response_time_ms) as avg_response_time,
                        MIN(response_time_ms) as min_response_time,
                        MAX(response_time_ms) as max_response_time
                    FROM checks
                    WHERE checked_at >= ?
                    GROUP BY url_name
                ),
                percentiles_24h AS (
                    SELECT
                        url_name,
                        MAX(CASE WHEN rn = CAST(total * 0.50 AS INTEGER) THEN response_time_ms END) as p50,
                        MAX(CASE WHEN rn = CAST(total * 0.95 AS INTEGER) THEN response_time_ms END) as p95,
                        MAX(CASE WHEN rn = CAST(total * 0.99 AS INTEGER) THEN response_time_ms END) as p99
                    FROM (
                        SELECT
                            url_name,
                            response_time_ms,
                            ROW_NUMBER() OVER (PARTITION BY url_name ORDER BY response_time_ms) as rn,
                            COUNT(*) OVER (PARTITION BY url_name) as total
                        FROM checks
                        WHERE checked_at >= ? AND response_time_ms IS NOT NULL
                    )
                    GROUP BY url_name
                ),
                stddev_24h AS (
                    SELECT
                        url_name,
                        AVG(response_time_ms) as mean_rt
                    FROM checks
                    WHERE checked_at >= ?
                    GROUP BY url_name
                ),
                variance_24h AS (
                    SELECT
                        c.url_name,
                        AVG((c.response_time_ms - s.mean_rt) * (c.response_time_ms - s.mean_rt)) as variance
                    FROM checks c
                    INNER JOIN stddev_24h s ON c.url_name = s.url_name
                    WHERE c.checked_at >= ?
                    GROUP BY c.url_name
                ),
                last_downtime AS (
                    SELECT
                        url_name,
                        MAX(checked_at) as downtime
                    FROM checks
                    WHERE is_up = 0
                    GROUP BY url_name
                ),
                consecutive_failures AS (
                    SELECT
                        url_name,
                        COUNT(*) as failures
                    FROM (
                        SELECT
                            url_name,
                            is_up,
                            SUM(CASE WHEN is_up = 1 THEN 1 ELSE 0 END)
                                OVER (PARTITION BY url_name ORDER BY checked_at DESC) as success_count
                        FROM checks
                    )
                    WHERE success_count = 0 AND is_up = 0
                    GROUP BY url_name
                )
                SELECT
                    l.url_name,
                    l.url,
                    l.is_up,
                    l.status_code,
                    l.response_time_ms,
                    l.error_message,
                    l.checked_at,
                    l.content_length,
                    l.server_header,
                    l.status_text,
                    l.ssl_cert_issuer,
                    l.ssl_cert_subject,
                    l.ssl_cert_expires_at,
                    l.ssl_cert_expires_in_days,
                    l.ssl_cert_error,
                    COALESCE(s.total_checks, 0) as checks_24h,
                    COALESCE(s.up_checks, 0) as up_checks_24h,
                    s.avg_response_time as avg_response_time_24h,
                    s.min_response_time as min_response_time_24h,
                    s.max_response_time as max_response_time_24h,
                    p.p50 as p50_response_time_24h,
                    p.p95 as p95_response_time_24h,
                    p.p99 as p99_response_time_24h,
                    v.variance as variance_24h,
                    d.downtime as last_downtime,
                    COALESCE(cf.failures, 0) as consecutive_failures
                FROM latest_checks l
                LEFT JOIN stats_24h s ON l.url_name = s.url_name
                LEFT JOIN percentiles_24h p ON l.url_name = p.url_name
                LEFT JOIN variance_24h v ON l.url_name = v.url_name
                LEFT JOIN last_downtime d ON l.url_name = d.url_name
                LEFT JOIN consecutive_failures cf ON l.url_name = cf.url_name
                WHERE l.rn = 1
                ORDER BY l.url_name
                """,
            (since_24h, since_24h, since_24h, since_24h),
        ).fetchall()

        result = [
            UrlStatus(
                url_name=row["url_name"],
                url=row["url"],
                is_up=bool(row["is_up"]),
                last_status_code=row["status_code"],
                last_response_time_ms=row["response_time_ms"],
                last_error=row["error_message"],
                last_check=datetime.fromisoformat(row["checked_at"]),
                checks_24h=row["checks_24h"],
                uptime_24h=((row["up_checks_24h"] / row["checks_24h"] * 100.0) if row["checks_24h"] > 0 else 0.0),
                avg_response_time_24h=row["avg_response_time_24h"],
                min_response_time_24h=row["min_response_time_24h"],
                max_response_time_24h=row["max_response_time_24h"],
                consecutive_failures=row["consecutive_failures"],
                last_downtime=(datetime.fromisoformat(row["last_downtime"]) if row["last_downtime"] else None),
                content_length=row["content_length"],
                server_header=row["server_header"],
                status_text=row["status_text"],
                p50_response_time_24h=row["p50_response_time_24h"],
                p95_response_time_24h=row["p95_response_time_24h"],
                p99_response_time_24h=row["p99_response_time_24h"],
                stddev_response_time_24h=(row["variance_24h"] ** 0.5) if row["variance_24h"] is not None else None,
                ssl_cert_issuer=row["ssl_cert_issuer"],
                ssl_cert_subject=row["ssl_cert_subject"],
                ssl_cert_expires_at=(
                    datetime.fromisoformat(row["ssl_cert_expires_at"]) if row["ssl_cert_expires_at"] else None
                ),
                ssl_cert_expires_in_days=row["ssl_cert_expires_in_days"],
                ssl_cert_error=row["ssl_cert_error"],
            )
            for row in rows
        ]

        return result

    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to get latest status: {e}")


def _revalidate_cache_background(conn: sqlite3.Connection) -> None:
    """Revalidate cache in background thread."""
    try:
        result = _fetch_latest_status_from_db(conn)
        _status_cache.set(result)
    except (DatabaseError, sqlite3.ProgrammingError):
        # Silently fail - stale data is still available
        # ProgrammingError occurs if connection was closed (e.g., during shutdown)
        pass


def get_latest_status(conn: sqlite3.Connection) -> list[UrlStatus]:
    """Get the latest status for all monitored URLs.

    Uses stale-while-revalidate caching strategy:
    - Fresh data (< 30s): Return immediately
    - Stale data (30s-5min): Return immediately, refresh in background
    - Expired data (> 5min): Block and fetch fresh data

    This ensures users almost never wait for the slow query.

    Args:
        conn: Database connection.

    Returns:
        List of UrlStatus objects, one per unique URL.

    Raises:
        DatabaseError: If the query fails and no cached data is available.
    """
    # Check cache - returns (data, needs_revalidation)
    cached, needs_revalidation = _status_cache.get()

    if cached is not None:
        # We have data to return immediately
        if needs_revalidation and _status_cache.mark_revalidating():
            # Spawn background thread to refresh cache
            thread = threading.Thread(
                target=_revalidate_cache_background,
                args=(conn,),
                daemon=True,
            )
            thread.start()
        return cached

    # No cached data available - must fetch synchronously
    result = _fetch_latest_status_from_db(conn)
    _status_cache.set(result)
    return result


def get_latest_status_by_name(conn: sqlite3.Connection, url_name: str) -> UrlStatus | None:
    """Get the latest status for a specific URL by name.

    Uses cache-first strategy: checks if the URL's status is already in the
    main status cache from get_latest_status(). If found and fresh/stale,
    returns immediately without hitting the database. This makes modal opening
    nearly instant when the dashboard has been viewed recently.

    Falls back to database query only when:
    - Cache is empty or expired
    - URL is not found in cache (new URL not yet in main status)

    Args:
        conn: Database connection.
        url_name: The name of the URL to query.

    Returns:
        UrlStatus object for the URL, or None if not found.

    Raises:
        DatabaseError: If the query fails.
    """
    # Check if URL is in the main status cache (from get_latest_status)
    cached, _ = _status_cache.get()
    if cached is not None:
        for status in cached:
            if status.url_name == url_name:
                return status

    # Not in cache - fall back to database query
    try:
        since_24h = (datetime.now(UTC) - timedelta(hours=24)).isoformat()

        row = conn.execute(
            """
            WITH latest_check AS (
                    SELECT
                        url_name,
                        url,
                        status_code,
                        response_time_ms,
                        is_up,
                        error_message,
                        checked_at,
                        content_length,
                        server_header,
                        status_text,
                        ssl_cert_issuer,
                        ssl_cert_subject,
                        ssl_cert_expires_at,
                        ssl_cert_expires_in_days,
                        ssl_cert_error
                    FROM checks
                    WHERE url_name = ?
                    ORDER BY checked_at DESC
                    LIMIT 1
                ),
                stats_24h AS (
                    SELECT
                        COUNT(*) as total_checks,
                        SUM(is_up) as up_checks,
                        AVG(response_time_ms) as avg_response_time,
                        MIN(response_time_ms) as min_response_time,
                        MAX(response_time_ms) as max_response_time
                    FROM checks
                    WHERE url_name = ? AND checked_at >= ?
                ),
                percentiles_24h AS (
                    SELECT
                        MAX(CASE WHEN rn = CAST(total * 0.50 AS INTEGER) THEN response_time_ms END) as p50,
                        MAX(CASE WHEN rn = CAST(total * 0.95 AS INTEGER) THEN response_time_ms END) as p95,
                        MAX(CASE WHEN rn = CAST(total * 0.99 AS INTEGER) THEN response_time_ms END) as p99
                    FROM (
                        SELECT
                            response_time_ms,
                            ROW_NUMBER() OVER (ORDER BY response_time_ms) as rn,
                            COUNT(*) OVER () as total
                        FROM checks
                        WHERE url_name = ? AND checked_at >= ? AND response_time_ms IS NOT NULL
                    )
                ),
                stddev_24h AS (
                    SELECT AVG(response_time_ms) as mean_rt
                    FROM checks
                    WHERE url_name = ? AND checked_at >= ?
                ),
                variance_24h AS (
                    SELECT AVG((c.response_time_ms - s.mean_rt) * (c.response_time_ms - s.mean_rt)) as variance
                    FROM checks c, stddev_24h s
                    WHERE c.url_name = ? AND c.checked_at >= ?
                ),
                last_downtime AS (
                    SELECT MAX(checked_at) as downtime
                    FROM checks
                    WHERE url_name = ? AND is_up = 0
                ),
                consecutive_failures AS (
                    SELECT COUNT(*) as failures
                    FROM (
                        SELECT
                            is_up,
                            SUM(CASE WHEN is_up = 1 THEN 1 ELSE 0 END)
                                OVER (ORDER BY checked_at DESC) as success_count
                        FROM checks
                        WHERE url_name = ?
                    )
                    WHERE success_count = 0 AND is_up = 0
                )
                SELECT
                    l.url_name,
                    l.url,
                    l.is_up,
                    l.status_code,
                    l.response_time_ms,
                    l.error_message,
                    l.checked_at,
                    l.content_length,
                    l.server_header,
                    l.status_text,
                    l.ssl_cert_issuer,
                    l.ssl_cert_subject,
                    l.ssl_cert_expires_at,
                    l.ssl_cert_expires_in_days,
                    l.ssl_cert_error,
                    COALESCE(s.total_checks, 0) as checks_24h,
                    COALESCE(s.up_checks, 0) as up_checks_24h,
                    s.avg_response_time as avg_response_time_24h,
                    s.min_response_time as min_response_time_24h,
                    s.max_response_time as max_response_time_24h,
                    p.p50 as p50_response_time_24h,
                    p.p95 as p95_response_time_24h,
                    p.p99 as p99_response_time_24h,
                    v.variance as variance_24h,
                    d.downtime as last_downtime,
                    COALESCE(cf.failures, 0) as consecutive_failures
                FROM latest_check l, stats_24h s, percentiles_24h p, variance_24h v, last_downtime d, consecutive_failures cf
                """,
            (
                url_name,
                url_name,
                since_24h,
                url_name,
                since_24h,
                url_name,
                since_24h,
                url_name,
                since_24h,
                url_name,
                url_name,
            ),
        ).fetchone()

        if row is None:
            return None

        return UrlStatus(
            url_name=row["url_name"],
            url=row["url"],
            is_up=bool(row["is_up"]),
            last_status_code=row["status_code"],
            last_response_time_ms=row["response_time_ms"],
            last_error=row["error_message"],
            last_check=datetime.fromisoformat(row["checked_at"]),
            checks_24h=row["checks_24h"],
            uptime_24h=((row["up_checks_24h"] / row["checks_24h"] * 100.0) if row["checks_24h"] > 0 else 0.0),
            avg_response_time_24h=row["avg_response_time_24h"],
            min_response_time_24h=row["min_response_time_24h"],
            max_response_time_24h=row["max_response_time_24h"],
            consecutive_failures=row["consecutive_failures"],
            last_downtime=(datetime.fromisoformat(row["last_downtime"]) if row["last_downtime"] else None),
            content_length=row["content_length"],
            server_header=row["server_header"],
            status_text=row["status_text"],
            p50_response_time_24h=row["p50_response_time_24h"],
            p95_response_time_24h=row["p95_response_time_24h"],
            p99_response_time_24h=row["p99_response_time_24h"],
            stddev_response_time_24h=(row["variance_24h"] ** 0.5) if row["variance_24h"] is not None else None,
            ssl_cert_issuer=row["ssl_cert_issuer"],
            ssl_cert_subject=row["ssl_cert_subject"],
            ssl_cert_expires_at=(
                datetime.fromisoformat(row["ssl_cert_expires_at"]) if row["ssl_cert_expires_at"] else None
            ),
            ssl_cert_expires_in_days=row["ssl_cert_expires_in_days"],
            ssl_cert_error=row["ssl_cert_error"],
        )

    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to get status for {url_name}: {e}")


def get_history(
    conn: sqlite3.Connection,
    url_name: str,
    since: datetime,
    limit: int | None = None,
) -> list[CheckResult]:
    """Get check history for a specific URL.

    Uses cache-first strategy: checks if the URL's history is already cached.
    If found and fresh (< 30s), returns immediately without hitting the database.
    This makes modal opening nearly instant when reopening within 30 seconds.

    Args:
        conn: Database connection.
        url_name: URL identifier to query.
        since: Return checks after this timestamp.
        limit: Maximum number of results to return (newest first).

    Returns:
        List of CheckResult objects, ordered by checked_at descending.

    Raises:
        DatabaseError: If the query fails.
    """
    # Check cache first (only for standard 24h queries with limit=100)
    # We cache this specific pattern since it's what the modal uses
    cached = _history_cache.get(url_name)
    if cached is not None:
        return cached

    try:
        query = """
            SELECT url_name, url, status_code, response_time_ms, is_up, error_message, checked_at,
                   content_length, server_header, status_text,
                   ssl_cert_issuer, ssl_cert_subject, ssl_cert_expires_at, ssl_cert_expires_in_days, ssl_cert_error,
                   ttfb_ms
            FROM checks
            WHERE url_name = ? AND checked_at >= ?
            ORDER BY checked_at DESC
        """
        params: tuple = (url_name, since.isoformat())

        if limit is not None:
            query += " LIMIT ?"
            params = (url_name, since.isoformat(), limit)

        rows = conn.execute(query, params).fetchall()

        results = [
            CheckResult(
                url_name=row["url_name"],
                url=row["url"],
                status_code=row["status_code"],
                response_time_ms=row["response_time_ms"],
                is_up=bool(row["is_up"]),
                error_message=row["error_message"],
                checked_at=datetime.fromisoformat(row["checked_at"]),
                content_length=row["content_length"],
                server_header=row["server_header"],
                status_text=row["status_text"],
                ssl_cert_issuer=row["ssl_cert_issuer"],
                ssl_cert_subject=row["ssl_cert_subject"],
                ssl_cert_expires_at=(
                    datetime.fromisoformat(row["ssl_cert_expires_at"]) if row["ssl_cert_expires_at"] else None
                ),
                ssl_cert_expires_in_days=row["ssl_cert_expires_in_days"],
                ssl_cert_error=row["ssl_cert_error"],
                ttfb_ms=row["ttfb_ms"],
            )
            for row in rows
        ]

        # Cache the results for subsequent requests
        _history_cache.set(url_name, results)

        return results

    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to get history: {e}")


def cleanup_old_checks(conn: sqlite3.Connection, retention_days: int) -> int:
    """Delete checks older than the retention period.

    Thread-safe: acquires global lock before database access.

    Args:
        conn: Database connection.
        retention_days: Delete checks older than this many days.

    Returns:
        Number of deleted records.

    Raises:
        DatabaseError: If the cleanup fails.
    """
    try:
        cutoff = (datetime.now(UTC) - timedelta(days=retention_days)).isoformat()

        with _db_lock:
            cursor = conn.execute(
                "DELETE FROM checks WHERE checked_at < ?",
                (cutoff,),
            )
            deleted = cursor.rowcount
            conn.commit()

        return deleted

    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to cleanup old checks: {e}")


def _get_metadata(conn: sqlite3.Connection, key: str) -> str | None:
    """Get metadata value by key.

    Args:
        conn: Database connection.
        key: Metadata key.

    Returns:
        Metadata value or None if key doesn't exist.
    """
    try:
        with _db_lock:
            cursor = conn.execute("SELECT value FROM _metadata WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None
    except sqlite3.Error:
        return None


def _set_metadata(conn: sqlite3.Connection, key: str, value: str) -> None:
    """Set metadata value by key (insert or update).

    Args:
        conn: Database connection.
        key: Metadata key.
        value: Metadata value.
    """
    try:
        with _db_lock:
            conn.execute(
                "INSERT OR REPLACE INTO _metadata (key, value) VALUES (?, ?)",
                (key, value),
            )
            conn.commit()
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to set metadata: {e}")


def maybe_vacuum(conn: sqlite3.Connection, vacuum_interval_days: int) -> bool:
    """Run VACUUM if configured interval has passed.

    VACUUM rebuilds the database file, reclaiming space freed by DELETE operations
    and defragmenting pages for better query performance.

    Thread-safe: acquires global lock before database access.

    Args:
        conn: Database connection.
        vacuum_interval_days: Run VACUUM if this many days have passed since last VACUUM.
                              Set to 0 to disable periodic VACUUM.

    Returns:
        True if VACUUM was performed, False otherwise.

    Raises:
        DatabaseError: If VACUUM fails.
    """
    import logging

    logger = logging.getLogger(__name__)

    if vacuum_interval_days <= 0:
        return False

    try:
        # Get last VACUUM timestamp
        last_vacuum_str = _get_metadata(conn, "last_vacuum")

        should_vacuum = False
        if last_vacuum_str is None:
            should_vacuum = True
        else:
            try:
                last_vacuum = datetime.fromisoformat(last_vacuum_str)
                days_since = (datetime.now(UTC) - last_vacuum).days
                should_vacuum = days_since >= vacuum_interval_days
            except ValueError:
                # Invalid timestamp - treat as never vacuumed
                should_vacuum = True

        if should_vacuum:
            logger.info("Running VACUUM on database (interval: %d days)", vacuum_interval_days)

            with _db_lock:
                conn.execute("VACUUM")
                conn.commit()

            # Record VACUUM timestamp
            _set_metadata(conn, "last_vacuum", datetime.now(UTC).isoformat())

            logger.info("VACUUM completed successfully")
            return True

        return False

    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to run VACUUM: {e}")


def get_url_names(conn: sqlite3.Connection) -> list[str]:
    """Get all unique URL names in the database.

    Thread-safe: acquires global lock before database access.

    Args:
        conn: Database connection.

    Returns:
        List of unique URL names.

    Raises:
        DatabaseError: If the query fails.
    """
    try:
        rows = conn.execute("SELECT DISTINCT url_name FROM checks ORDER BY url_name").fetchall()
        return [row["url_name"] for row in rows]

    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to get URL names: {e}")


def delete_all_checks(conn: sqlite3.Connection) -> int:
    """Delete all check records from the database.

    Thread-safe: acquires global lock before database access.

    Args:
        conn: Database connection.

    Returns:
        Number of deleted records.

    Raises:
        DatabaseError: If the deletion fails.
    """
    try:
        with _db_lock:
            cursor = conn.execute("DELETE FROM checks")
            deleted = cursor.rowcount
            conn.commit()
        return deleted

    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to delete all checks: {e}")
