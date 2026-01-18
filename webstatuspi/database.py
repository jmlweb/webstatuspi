"""SQLite database operations for URL check persistence."""

import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

from .models import CheckResult, UrlStatus


class DatabaseError(Exception):
    """Raised when a database operation fails."""
    pass


# Global lock for thread-safe database access.
# SQLite allows concurrent reads but only one writer at a time.
# This lock ensures safe access from multiple threads (monitor, API handlers).
_db_lock = threading.Lock()


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
                checked_at TEXT NOT NULL
            )
        """)

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
                (url_name, url, status_code, response_time_ms, is_up, error_message, checked_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.url_name,
                    result.url,
                    result.status_code,
                    result.response_time_ms,
                    1 if result.is_up else 0,
                    result.error_message,
                    result.checked_at.isoformat(),
                ),
            )
            conn.commit()
    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to insert check result: {e}")


def get_latest_status(conn: sqlite3.Connection) -> List[UrlStatus]:
    """Get the latest status for all monitored URLs.

    Thread-safe: acquires global lock before database access.
    Includes 24-hour statistics (total checks and uptime percentage).

    Args:
        conn: Database connection.

    Returns:
        List of UrlStatus objects, one per unique URL.

    Raises:
        DatabaseError: If the query fails.
    """
    try:
        since_24h = (datetime.utcnow() - timedelta(hours=24)).isoformat()

        with _db_lock:
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
                        ROW_NUMBER() OVER (PARTITION BY url_name ORDER BY checked_at DESC) as rn
                    FROM checks
                ),
                stats_24h AS (
                    SELECT
                        url_name,
                        COUNT(*) as total_checks,
                        SUM(is_up) as up_checks
                    FROM checks
                    WHERE checked_at >= ?
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
                    COALESCE(s.total_checks, 0) as checks_24h,
                    COALESCE(s.up_checks, 0) as up_checks_24h
                FROM latest_checks l
                LEFT JOIN stats_24h s ON l.url_name = s.url_name
                WHERE l.rn = 1
                ORDER BY l.url_name
                """,
                (since_24h,),
            ).fetchall()

        return [
            UrlStatus(
                url_name=row["url_name"],
                url=row["url"],
                is_up=bool(row["is_up"]),
                last_status_code=row["status_code"],
                last_response_time_ms=row["response_time_ms"],
                last_error=row["error_message"],
                last_check=datetime.fromisoformat(row["checked_at"]),
                checks_24h=row["checks_24h"],
                uptime_24h=(
                    (row["up_checks_24h"] / row["checks_24h"] * 100.0)
                    if row["checks_24h"] > 0
                    else 0.0
                ),
            )
            for row in rows
        ]

    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to get latest status: {e}")


def get_latest_status_by_name(conn: sqlite3.Connection, url_name: str) -> Optional[UrlStatus]:
    """Get the latest status for a specific URL by name.

    Thread-safe: acquires global lock before database access.
    More efficient than get_latest_status() when querying a single URL.

    Args:
        conn: Database connection.
        url_name: The name of the URL to query.

    Returns:
        UrlStatus object for the URL, or None if not found.

    Raises:
        DatabaseError: If the query fails.
    """
    try:
        since_24h = (datetime.utcnow() - timedelta(hours=24)).isoformat()

        with _db_lock:
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
                        checked_at
                    FROM checks
                    WHERE url_name = ?
                    ORDER BY checked_at DESC
                    LIMIT 1
                ),
                stats_24h AS (
                    SELECT
                        COUNT(*) as total_checks,
                        SUM(is_up) as up_checks
                    FROM checks
                    WHERE url_name = ? AND checked_at >= ?
                )
                SELECT
                    l.url_name,
                    l.url,
                    l.is_up,
                    l.status_code,
                    l.response_time_ms,
                    l.error_message,
                    l.checked_at,
                    COALESCE(s.total_checks, 0) as checks_24h,
                    COALESCE(s.up_checks, 0) as up_checks_24h
                FROM latest_check l, stats_24h s
                """,
                (url_name, url_name, since_24h),
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
            uptime_24h=(
                (row["up_checks_24h"] / row["checks_24h"] * 100.0)
                if row["checks_24h"] > 0
                else 0.0
            ),
        )

    except sqlite3.Error as e:
        raise DatabaseError(f"Failed to get status for {url_name}: {e}")


def get_history(
    conn: sqlite3.Connection,
    url_name: str,
    since: datetime,
    limit: Optional[int] = None,
) -> List[CheckResult]:
    """Get check history for a specific URL.

    Thread-safe: acquires global lock before database access.

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
    try:
        query = """
            SELECT url_name, url, status_code, response_time_ms, is_up, error_message, checked_at
            FROM checks
            WHERE url_name = ? AND checked_at >= ?
            ORDER BY checked_at DESC
        """
        params: tuple = (url_name, since.isoformat())

        if limit is not None:
            query += " LIMIT ?"
            params = (url_name, since.isoformat(), limit)

        with _db_lock:
            rows = conn.execute(query, params).fetchall()

        return [
            CheckResult(
                url_name=row["url_name"],
                url=row["url"],
                status_code=row["status_code"],
                response_time_ms=row["response_time_ms"],
                is_up=bool(row["is_up"]),
                error_message=row["error_message"],
                checked_at=datetime.fromisoformat(row["checked_at"]),
            )
            for row in rows
        ]

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
        cutoff = (datetime.utcnow() - timedelta(days=retention_days)).isoformat()

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


def get_url_names(conn: sqlite3.Connection) -> List[str]:
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
        with _db_lock:
            rows = conn.execute(
                "SELECT DISTINCT url_name FROM checks ORDER BY url_name"
            ).fetchall()
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
