"""Tests for the database module."""

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from webstatuspi.database import (
    cleanup_old_checks,
    get_history,
    get_latest_status,
    get_url_names,
    init_db,
    insert_check,
)
from webstatuspi.models import CheckResult


@pytest.fixture
def db_path(tmp_path: Path) -> str:
    """Create a temporary database path."""
    return str(tmp_path / "test.db")


@pytest.fixture
def db_conn(db_path: str) -> sqlite3.Connection:
    """Create a database connection with initialized tables."""
    conn = init_db(db_path)
    yield conn
    conn.close()


@pytest.fixture
def sample_check() -> CheckResult:
    """Create a sample check result."""
    return CheckResult(
        url_name="TEST_URL",
        url="https://example.com",
        status_code=200,
        response_time_ms=150,
        is_up=True,
        error_message=None,
        checked_at=datetime.now(UTC),
    )


class TestInitDb:
    """Tests for init_db function."""

    def test_creates_database_file(self, db_path: str) -> None:
        """Database file is created at specified path."""
        conn = init_db(db_path)
        conn.close()
        assert Path(db_path).exists()

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Parent directories are created if they don't exist."""
        nested_path = str(tmp_path / "nested" / "dir" / "test.db")
        conn = init_db(nested_path)
        conn.close()
        assert Path(nested_path).exists()

    def test_creates_checks_table(self, db_conn: sqlite3.Connection) -> None:
        """Checks table is created with correct schema."""
        cursor = db_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='checks'")
        assert cursor.fetchone() is not None

    def test_creates_indexes(self, db_conn: sqlite3.Connection) -> None:
        """Required indexes are created."""
        cursor = db_conn.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = {row[0] for row in cursor.fetchall()}
        assert "idx_checks_url_name" in indexes
        assert "idx_checks_checked_at" in indexes

    def test_enables_wal_mode(self, db_conn: sqlite3.Connection) -> None:
        """WAL mode is enabled for concurrent reads."""
        cursor = db_conn.execute("PRAGMA journal_mode")
        mode = cursor.fetchone()[0]
        assert mode.lower() == "wal"

    def test_idempotent_initialization(self, db_path: str) -> None:
        """Multiple init calls don't cause errors."""
        conn1 = init_db(db_path)
        conn1.close()
        conn2 = init_db(db_path)
        conn2.close()


class TestInsertCheck:
    """Tests for insert_check function."""

    def test_inserts_successful_check(self, db_conn: sqlite3.Connection, sample_check: CheckResult) -> None:
        """Successful check is inserted correctly."""
        insert_check(db_conn, sample_check)

        cursor = db_conn.execute("SELECT * FROM checks WHERE url_name = ?", ("TEST_URL",))
        row = cursor.fetchone()

        assert row["url_name"] == "TEST_URL"
        assert row["url"] == "https://example.com"
        assert row["status_code"] == 200
        assert row["response_time_ms"] == 150
        assert row["is_up"] == 1
        assert row["error_message"] is None

    def test_inserts_failed_check(self, db_conn: sqlite3.Connection) -> None:
        """Failed check with error message is inserted correctly."""
        check = CheckResult(
            url_name="FAIL_URL",
            url="https://fail.example.com",
            status_code=None,
            response_time_ms=0,
            is_up=False,
            error_message="Connection timeout",
            checked_at=datetime.now(UTC),
        )
        insert_check(db_conn, check)

        cursor = db_conn.execute("SELECT * FROM checks WHERE url_name = ?", ("FAIL_URL",))
        row = cursor.fetchone()

        assert row["url_name"] == "FAIL_URL"
        assert row["status_code"] is None
        assert row["is_up"] == 0
        assert row["error_message"] == "Connection timeout"

    def test_inserts_multiple_checks(self, db_conn: sqlite3.Connection, sample_check: CheckResult) -> None:
        """Multiple checks can be inserted."""
        for _ in range(5):
            insert_check(db_conn, sample_check)

        cursor = db_conn.execute("SELECT COUNT(*) FROM checks")
        count = cursor.fetchone()[0]
        assert count == 5


class TestGetLatestStatus:
    """Tests for get_latest_status function."""

    def test_returns_empty_list_for_empty_db(self, db_conn: sqlite3.Connection) -> None:
        """Empty list returned when no checks exist."""
        result = get_latest_status(db_conn)
        assert result == []

    def test_returns_latest_check_per_url(self, db_conn: sqlite3.Connection) -> None:
        """Only the latest check per URL is returned."""
        now = datetime.now(UTC)

        # Insert older check
        old_check = CheckResult(
            url_name="TEST_URL",
            url="https://example.com",
            status_code=500,
            response_time_ms=100,
            is_up=False,
            error_message="Server error",
            checked_at=now - timedelta(hours=1),
        )
        insert_check(db_conn, old_check)

        # Insert newer check
        new_check = CheckResult(
            url_name="TEST_URL",
            url="https://example.com",
            status_code=200,
            response_time_ms=150,
            is_up=True,
            error_message=None,
            checked_at=now,
        )
        insert_check(db_conn, new_check)

        result = get_latest_status(db_conn)

        assert len(result) == 1
        assert result[0].is_up is True
        assert result[0].last_status_code == 200

    def test_calculates_24h_statistics(self, db_conn: sqlite3.Connection) -> None:
        """24-hour check count and uptime percentage are calculated."""
        now = datetime.now(UTC)

        # Insert 4 checks: 3 up, 1 down (75% uptime)
        for i, is_up in enumerate([True, True, True, False]):
            check = CheckResult(
                url_name="STATS_URL",
                url="https://stats.example.com",
                status_code=200 if is_up else 500,
                response_time_ms=100,
                is_up=is_up,
                error_message=None if is_up else "Error",
                checked_at=now - timedelta(hours=i),
            )
            insert_check(db_conn, check)

        result = get_latest_status(db_conn)

        assert len(result) == 1
        assert result[0].checks_24h == 4
        assert result[0].uptime_24h == 75.0

    def test_excludes_old_checks_from_stats(self, db_conn: sqlite3.Connection) -> None:
        """Checks older than 24h are excluded from statistics."""
        now = datetime.now(UTC)

        # Insert check within 24h
        recent = CheckResult(
            url_name="OLD_URL",
            url="https://old.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=now,
        )
        insert_check(db_conn, recent)

        # Insert check older than 24h
        old = CheckResult(
            url_name="OLD_URL",
            url="https://old.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=now - timedelta(hours=25),
        )
        insert_check(db_conn, old)

        result = get_latest_status(db_conn)

        assert result[0].checks_24h == 1

    def test_returns_multiple_urls(self, db_conn: sqlite3.Connection) -> None:
        """Status for all URLs is returned."""
        now = datetime.now(UTC)

        for name in ["URL_A", "URL_B", "URL_C"]:
            check = CheckResult(
                url_name=name,
                url=f"https://{name.lower()}.example.com",
                status_code=200,
                response_time_ms=100,
                is_up=True,
                error_message=None,
                checked_at=now,
            )
            insert_check(db_conn, check)

        result = get_latest_status(db_conn)

        assert len(result) == 3
        names = {s.url_name for s in result}
        assert names == {"URL_A", "URL_B", "URL_C"}


class TestGetHistory:
    """Tests for get_history function."""

    def test_returns_empty_list_for_no_matches(self, db_conn: sqlite3.Connection) -> None:
        """Empty list returned when no history exists."""
        result = get_history(db_conn, "NONEXISTENT", datetime.now(UTC) - timedelta(days=1))
        assert result == []

    def test_filters_by_url_name(self, db_conn: sqlite3.Connection) -> None:
        """Only returns history for specified URL."""
        now = datetime.now(UTC)

        for name in ["URL_A", "URL_B"]:
            check = CheckResult(
                url_name=name,
                url=f"https://{name.lower()}.example.com",
                status_code=200,
                response_time_ms=100,
                is_up=True,
                error_message=None,
                checked_at=now,
            )
            insert_check(db_conn, check)

        result = get_history(db_conn, "URL_A", now - timedelta(hours=1))

        assert len(result) == 1
        assert result[0].url_name == "URL_A"

    def test_filters_by_time_range(self, db_conn: sqlite3.Connection) -> None:
        """Only returns checks after the since timestamp."""
        now = datetime.now(UTC)

        # Insert checks at different times
        for hours_ago in [1, 5, 10, 25]:
            check = CheckResult(
                url_name="TIME_URL",
                url="https://time.example.com",
                status_code=200,
                response_time_ms=100,
                is_up=True,
                error_message=None,
                checked_at=now - timedelta(hours=hours_ago),
            )
            insert_check(db_conn, check)

        # Query for last 12 hours
        result = get_history(db_conn, "TIME_URL", now - timedelta(hours=12))

        assert len(result) == 3  # 1h, 5h, 10h ago

    def test_orders_by_newest_first(self, db_conn: sqlite3.Connection) -> None:
        """Results are ordered by checked_at descending."""
        now = datetime.now(UTC)

        for hours_ago in [1, 2, 3]:
            check = CheckResult(
                url_name="ORDER_URL",
                url="https://order.example.com",
                status_code=200,
                response_time_ms=100,
                is_up=True,
                error_message=None,
                checked_at=now - timedelta(hours=hours_ago),
            )
            insert_check(db_conn, check)

        result = get_history(db_conn, "ORDER_URL", now - timedelta(hours=5))

        assert len(result) == 3
        assert result[0].checked_at > result[1].checked_at > result[2].checked_at

    def test_respects_limit(self, db_conn: sqlite3.Connection) -> None:
        """Limit parameter restricts number of results."""
        now = datetime.now(UTC)

        for i in range(10):
            check = CheckResult(
                url_name="LIMIT_URL",
                url="https://limit.example.com",
                status_code=200,
                response_time_ms=100,
                is_up=True,
                error_message=None,
                checked_at=now - timedelta(minutes=i),
            )
            insert_check(db_conn, check)

        result = get_history(db_conn, "LIMIT_URL", now - timedelta(hours=1), limit=5)

        assert len(result) == 5


class TestCleanupOldChecks:
    """Tests for cleanup_old_checks function."""

    def test_deletes_old_checks(self, db_conn: sqlite3.Connection) -> None:
        """Checks older than retention period are deleted."""
        now = datetime.now(UTC)

        # Insert checks at different ages
        for days_ago in [1, 5, 10, 15]:
            check = CheckResult(
                url_name="CLEANUP_URL",
                url="https://cleanup.example.com",
                status_code=200,
                response_time_ms=100,
                is_up=True,
                error_message=None,
                checked_at=now - timedelta(days=days_ago),
            )
            insert_check(db_conn, check)

        deleted = cleanup_old_checks(db_conn, retention_days=7)

        assert deleted == 2  # 10 and 15 days old

        cursor = db_conn.execute("SELECT COUNT(*) FROM checks")
        remaining = cursor.fetchone()[0]
        assert remaining == 2

    def test_returns_deleted_count(self, db_conn: sqlite3.Connection) -> None:
        """Returns number of deleted records."""
        now = datetime.now(UTC)

        for i in range(5):
            check = CheckResult(
                url_name="COUNT_URL",
                url="https://count.example.com",
                status_code=200,
                response_time_ms=100,
                is_up=True,
                error_message=None,
                checked_at=now - timedelta(days=i + 10),
            )
            insert_check(db_conn, check)

        deleted = cleanup_old_checks(db_conn, retention_days=7)

        assert deleted == 5

    def test_handles_empty_database(self, db_conn: sqlite3.Connection) -> None:
        """No error when cleaning empty database."""
        deleted = cleanup_old_checks(db_conn, retention_days=7)
        assert deleted == 0


class TestGetUrlNames:
    """Tests for get_url_names function."""

    def test_returns_empty_list_for_empty_db(self, db_conn: sqlite3.Connection) -> None:
        """Empty list returned when no URLs exist."""
        result = get_url_names(db_conn)
        assert result == []

    def test_returns_unique_names(self, db_conn: sqlite3.Connection) -> None:
        """Returns unique URL names."""
        now = datetime.now(UTC)

        # Insert multiple checks for same URLs
        for name in ["URL_A", "URL_B", "URL_A", "URL_C", "URL_B"]:
            check = CheckResult(
                url_name=name,
                url=f"https://{name.lower()}.example.com",
                status_code=200,
                response_time_ms=100,
                is_up=True,
                error_message=None,
                checked_at=now,
            )
            insert_check(db_conn, check)

        result = get_url_names(db_conn)

        assert result == ["URL_A", "URL_B", "URL_C"]

    def test_returns_sorted_names(self, db_conn: sqlite3.Connection) -> None:
        """Names are returned in alphabetical order."""
        now = datetime.now(UTC)

        for name in ["Z_URL", "A_URL", "M_URL"]:
            check = CheckResult(
                url_name=name,
                url=f"https://{name.lower()}.example.com",
                status_code=200,
                response_time_ms=100,
                is_up=True,
                error_message=None,
                checked_at=now,
            )
            insert_check(db_conn, check)

        result = get_url_names(db_conn)

        assert result == ["A_URL", "M_URL", "Z_URL"]


class TestExtendedMetrics:
    """Tests for extended metrics calculated in get_latest_status."""

    def test_avg_response_time_calculated_correctly(self, db_conn: sqlite3.Connection) -> None:
        """Average response time is calculated from checks in last 24h."""
        now = datetime.now(UTC)

        # Insert checks with different response times
        response_times = [100, 200, 150, 250]
        for i, rt in enumerate(response_times):
            check = CheckResult(
                url_name="METRICS_URL",
                url="https://metrics.example.com",
                status_code=200,
                response_time_ms=rt,
                is_up=True,
                error_message=None,
                checked_at=now - timedelta(hours=i),
            )
            insert_check(db_conn, check)

        result = get_latest_status(db_conn)

        assert len(result) == 1
        expected_avg = sum(response_times) / len(response_times)
        assert result[0].avg_response_time_24h == expected_avg

    def test_min_response_time_calculated_correctly(self, db_conn: sqlite3.Connection) -> None:
        """Minimum response time is calculated from checks in last 24h."""
        now = datetime.now(UTC)

        # Insert checks with different response times
        response_times = [100, 200, 50, 250]
        for i, rt in enumerate(response_times):
            check = CheckResult(
                url_name="MIN_URL",
                url="https://min.example.com",
                status_code=200,
                response_time_ms=rt,
                is_up=True,
                error_message=None,
                checked_at=now - timedelta(hours=i),
            )
            insert_check(db_conn, check)

        result = get_latest_status(db_conn)

        assert len(result) == 1
        assert result[0].min_response_time_24h == 50

    def test_max_response_time_calculated_correctly(self, db_conn: sqlite3.Connection) -> None:
        """Maximum response time is calculated from checks in last 24h."""
        now = datetime.now(UTC)

        # Insert checks with different response times
        response_times = [100, 200, 150, 250]
        for i, rt in enumerate(response_times):
            check = CheckResult(
                url_name="MAX_URL",
                url="https://max.example.com",
                status_code=200,
                response_time_ms=rt,
                is_up=True,
                error_message=None,
                checked_at=now - timedelta(hours=i),
            )
            insert_check(db_conn, check)

        result = get_latest_status(db_conn)

        assert len(result) == 1
        assert result[0].max_response_time_24h == 250

    def test_response_time_stats_none_when_no_checks_24h(self, db_conn: sqlite3.Connection) -> None:
        """Response time stats return None when no checks in last 24h."""
        now = datetime.now(UTC)

        # Insert check older than 24h
        check = CheckResult(
            url_name="OLD_URL",
            url="https://old.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=now - timedelta(hours=25),
        )
        insert_check(db_conn, check)

        result = get_latest_status(db_conn)

        assert len(result) == 1
        assert result[0].avg_response_time_24h is None
        assert result[0].min_response_time_24h is None
        assert result[0].max_response_time_24h is None

    def test_consecutive_failures_returns_zero_when_last_check_successful(self, db_conn: sqlite3.Connection) -> None:
        """Consecutive failures is 0 when last check was successful."""
        now = datetime.now(UTC)

        # Insert failed checks followed by successful check
        for i in range(3):
            check = CheckResult(
                url_name="RECOVER_URL",
                url="https://recover.example.com",
                status_code=500,
                response_time_ms=100,
                is_up=False,
                error_message="Server error",
                checked_at=now - timedelta(hours=i + 1),
            )
            insert_check(db_conn, check)

        # Most recent check is successful
        success_check = CheckResult(
            url_name="RECOVER_URL",
            url="https://recover.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=now,
        )
        insert_check(db_conn, success_check)

        result = get_latest_status(db_conn)

        assert len(result) == 1
        assert result[0].consecutive_failures == 0

    def test_consecutive_failures_counts_recent_failures(self, db_conn: sqlite3.Connection) -> None:
        """Consecutive failures counts consecutive failed checks from most recent."""
        now = datetime.now(UTC)

        # Insert successful check (older)
        success_check = CheckResult(
            url_name="FAIL_URL",
            url="https://fail.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=now - timedelta(hours=4),
        )
        insert_check(db_conn, success_check)

        # Insert 3 consecutive failures (most recent)
        for i in range(3):
            check = CheckResult(
                url_name="FAIL_URL",
                url="https://fail.example.com",
                status_code=500,
                response_time_ms=100,
                is_up=False,
                error_message="Server error",
                checked_at=now - timedelta(hours=2 - i),
            )
            insert_check(db_conn, check)

        result = get_latest_status(db_conn)

        assert len(result) == 1
        assert result[0].consecutive_failures == 3

    def test_consecutive_failures_resets_after_success(self, db_conn: sqlite3.Connection) -> None:
        """Consecutive failures resets to 0 after a successful check."""
        now = datetime.now(UTC)

        # Insert old failures
        for i in range(5):
            check = CheckResult(
                url_name="RESET_URL",
                url="https://reset.example.com",
                status_code=500,
                response_time_ms=100,
                is_up=False,
                error_message="Server error",
                checked_at=now - timedelta(hours=i + 2),
            )
            insert_check(db_conn, check)

        # Insert successful check (resets the counter)
        success_check = CheckResult(
            url_name="RESET_URL",
            url="https://reset.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=now - timedelta(hours=1),
        )
        insert_check(db_conn, success_check)

        # Insert recent failure
        fail_check = CheckResult(
            url_name="RESET_URL",
            url="https://reset.example.com",
            status_code=500,
            response_time_ms=100,
            is_up=False,
            error_message="Server error",
            checked_at=now,
        )
        insert_check(db_conn, fail_check)

        result = get_latest_status(db_conn)

        assert len(result) == 1
        assert result[0].consecutive_failures == 1

    def test_last_downtime_returns_none_when_never_failed(self, db_conn: sqlite3.Connection) -> None:
        """Last downtime is None when URL has never failed."""
        now = datetime.now(UTC)

        # Insert only successful checks
        for i in range(5):
            check = CheckResult(
                url_name="STABLE_URL",
                url="https://stable.example.com",
                status_code=200,
                response_time_ms=100,
                is_up=True,
                error_message=None,
                checked_at=now - timedelta(hours=i),
            )
            insert_check(db_conn, check)

        result = get_latest_status(db_conn)

        assert len(result) == 1
        assert result[0].last_downtime is None

    def test_last_downtime_returns_most_recent_failure(self, db_conn: sqlite3.Connection) -> None:
        """Last downtime returns timestamp of most recent failure."""
        now = datetime.now(UTC)
        most_recent_failure = now - timedelta(hours=2)

        # Insert old failure
        old_fail = CheckResult(
            url_name="DOWN_URL",
            url="https://down.example.com",
            status_code=500,
            response_time_ms=100,
            is_up=False,
            error_message="Server error",
            checked_at=now - timedelta(hours=10),
        )
        insert_check(db_conn, old_fail)

        # Insert most recent failure
        recent_fail = CheckResult(
            url_name="DOWN_URL",
            url="https://down.example.com",
            status_code=500,
            response_time_ms=100,
            is_up=False,
            error_message="Server error",
            checked_at=most_recent_failure,
        )
        insert_check(db_conn, recent_fail)

        # Insert successful check after the failure
        success_check = CheckResult(
            url_name="DOWN_URL",
            url="https://down.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=now,
        )
        insert_check(db_conn, success_check)

        result = get_latest_status(db_conn)

        assert len(result) == 1
        assert result[0].last_downtime == most_recent_failure

    def test_content_length_stored_and_retrieved(self, db_conn: sqlite3.Connection) -> None:
        """Content-Length is stored and retrieved correctly."""
        now = datetime.now(UTC)

        check = CheckResult(
            url_name="CONTENT_URL",
            url="https://content.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=now,
            content_length=1024,
        )
        insert_check(db_conn, check)

        result = get_latest_status(db_conn)

        assert len(result) == 1
        assert result[0].content_length == 1024

    def test_content_length_handles_none(self, db_conn: sqlite3.Connection) -> None:
        """Content-Length handles None when header not present."""
        now = datetime.now(UTC)

        check = CheckResult(
            url_name="NO_CONTENT_URL",
            url="https://nocontent.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=now,
            content_length=None,
        )
        insert_check(db_conn, check)

        result = get_latest_status(db_conn)

        assert len(result) == 1
        assert result[0].content_length is None


class TestExtendedMetricsByName:
    """Tests for extended metrics in get_latest_status_by_name."""

    def test_response_time_stats_by_name(self, db_conn: sqlite3.Connection) -> None:
        """Response time stats are calculated correctly for specific URL."""
        now = datetime.now(UTC)

        # Insert checks for URL_A
        response_times = [100, 200, 150]
        for i, rt in enumerate(response_times):
            check = CheckResult(
                url_name="URL_A",
                url="https://a.example.com",
                status_code=200,
                response_time_ms=rt,
                is_up=True,
                error_message=None,
                checked_at=now - timedelta(hours=i),
            )
            insert_check(db_conn, check)

        # Insert checks for URL_B (should not affect URL_A stats)
        check_b = CheckResult(
            url_name="URL_B",
            url="https://b.example.com",
            status_code=200,
            response_time_ms=999,
            is_up=True,
            error_message=None,
            checked_at=now,
        )
        insert_check(db_conn, check_b)

        from webstatuspi.database import get_latest_status_by_name

        result = get_latest_status_by_name(db_conn, "URL_A")

        assert result is not None
        assert result.avg_response_time_24h == sum(response_times) / len(response_times)
        assert result.min_response_time_24h == 100
        assert result.max_response_time_24h == 200

    def test_consecutive_failures_by_name(self, db_conn: sqlite3.Connection) -> None:
        """Consecutive failures counted correctly for specific URL."""
        now = datetime.now(UTC)

        # Insert failures for URL_A
        for i in range(3):
            check = CheckResult(
                url_name="URL_A",
                url="https://a.example.com",
                status_code=500,
                response_time_ms=100,
                is_up=False,
                error_message="Error",
                checked_at=now - timedelta(hours=2 - i),
            )
            insert_check(db_conn, check)

        from webstatuspi.database import get_latest_status_by_name

        result = get_latest_status_by_name(db_conn, "URL_A")

        assert result is not None
        assert result.consecutive_failures == 3

    def test_last_downtime_by_name(self, db_conn: sqlite3.Connection) -> None:
        """Last downtime returned correctly for specific URL."""
        now = datetime.now(UTC)
        downtime = now - timedelta(hours=5)

        # Insert failure
        fail_check = CheckResult(
            url_name="URL_A",
            url="https://a.example.com",
            status_code=500,
            response_time_ms=100,
            is_up=False,
            error_message="Error",
            checked_at=downtime,
        )
        insert_check(db_conn, fail_check)

        # Insert success after
        success_check = CheckResult(
            url_name="URL_A",
            url="https://a.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=now,
        )
        insert_check(db_conn, success_check)

        from webstatuspi.database import get_latest_status_by_name

        result = get_latest_status_by_name(db_conn, "URL_A")

        assert result is not None
        assert result.last_downtime == downtime

    def test_content_length_by_name(self, db_conn: sqlite3.Connection) -> None:
        """Content-Length retrieved correctly for specific URL."""
        now = datetime.now(UTC)

        check = CheckResult(
            url_name="URL_A",
            url="https://a.example.com",
            status_code=200,
            response_time_ms=100,
            is_up=True,
            error_message=None,
            checked_at=now,
            content_length=2048,
        )
        insert_check(db_conn, check)

        from webstatuspi.database import get_latest_status_by_name

        result = get_latest_status_by_name(db_conn, "URL_A")

        assert result is not None
        assert result.content_length == 2048

    def test_returns_none_for_nonexistent_url(self, db_conn: sqlite3.Connection) -> None:
        """Returns None when URL name doesn't exist."""
        from webstatuspi.database import get_latest_status_by_name

        result = get_latest_status_by_name(db_conn, "NONEXISTENT")

        assert result is None
