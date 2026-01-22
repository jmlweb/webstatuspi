"""Tests for the configuration module."""

from pathlib import Path

import pytest

from webstatuspi.config import (
    ApiConfig,
    Config,
    ConfigError,
    DatabaseConfig,
    DisplayConfig,
    MonitorConfig,
    UrlConfig,
    _parse_success_codes,
    load_config,
)


@pytest.fixture
def config_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for config files."""
    return tmp_path


@pytest.fixture
def valid_config_content() -> str:
    """Return a valid configuration YAML content."""
    return """urls:
  - name: Google
    url: https://google.com
    timeout: 10
  - name: GitHub
    url: https://github.com

monitor:
  interval: 60

database:
  path: ./data/status.db
  retention_days: 7

display:
  enabled: true
  cycle_interval: 5

api:
  enabled: true
  port: 8080
"""


class TestUrlConfig:
    """Tests for UrlConfig dataclass."""

    def test_creates_valid_url_config(self) -> None:
        """Valid URL configuration can be created."""
        url_config = UrlConfig(
            name="TestURL",
            url="https://example.com",
            timeout=15,
        )
        assert url_config.name == "TestURL"
        assert url_config.url == "https://example.com"
        assert url_config.timeout == 15

    def test_url_config_with_defaults(self) -> None:
        """UrlConfig uses default timeout of 10 seconds."""
        url_config = UrlConfig(
            name="TestURL",
            url="https://example.com",
        )
        assert url_config.timeout == 10

    def test_rejects_empty_name(self) -> None:
        """Empty URL name is rejected."""
        with pytest.raises(ConfigError, match="URL name cannot be empty"):
            UrlConfig(name="", url="https://example.com")

    def test_rejects_name_exceeding_10_chars(self) -> None:
        """URL name longer than 10 characters is rejected."""
        with pytest.raises(ConfigError, match="exceeds 10 characters"):
            UrlConfig(
                name="VeryLongNameThatExceeds10",
                url="https://example.com",
            )

    def test_accepts_name_exactly_10_chars(self) -> None:
        """URL name exactly 10 characters is accepted."""
        url_config = UrlConfig(
            name="TenChars!",  # exactly 10 characters
            url="https://example.com",
        )
        assert url_config.name == "TenChars!"

    def test_rejects_empty_url(self) -> None:
        """Empty URL is rejected."""
        with pytest.raises(ConfigError, match="URL cannot be empty"):
            UrlConfig(name="Test", url="")

    def test_rejects_url_without_protocol(self) -> None:
        """URL without http/https protocol is rejected."""
        with pytest.raises(ConfigError, match="must start with http"):
            UrlConfig(name="Test", url="example.com")

    def test_accepts_http_protocol(self) -> None:
        """URL with http protocol is accepted."""
        url_config = UrlConfig(
            name="Test",
            url="http://example.com",
        )
        assert url_config.url == "http://example.com"

    def test_accepts_https_protocol(self) -> None:
        """URL with https protocol is accepted."""
        url_config = UrlConfig(
            name="Test",
            url="https://example.com",
        )
        assert url_config.url == "https://example.com"

    def test_rejects_timeout_less_than_1(self) -> None:
        """Timeout less than 1 second is rejected."""
        with pytest.raises(ConfigError, match="Timeout must be at least 1 second"):
            UrlConfig(
                name="Test",
                url="https://example.com",
                timeout=0,
            )

    def test_accepts_timeout_of_1(self) -> None:
        """Timeout of 1 second is accepted."""
        url_config = UrlConfig(
            name="Test",
            url="https://example.com",
            timeout=1,
        )
        assert url_config.timeout == 1

    def test_accepts_success_codes_single(self) -> None:
        """UrlConfig accepts single success codes."""
        url_config = UrlConfig(
            name="Test",
            url="https://example.com",
            success_codes=[200, 201, 202],
        )
        assert url_config.success_codes == [200, 201, 202]

    def test_accepts_success_codes_with_ranges(self) -> None:
        """UrlConfig accepts success codes with ranges."""
        url_config = UrlConfig(
            name="Test",
            url="https://example.com",
            success_codes=[(200, 299), 400],
        )
        assert url_config.success_codes == [(200, 299), 400]

    def test_success_codes_default_none(self) -> None:
        """UrlConfig defaults success_codes to None."""
        url_config = UrlConfig(
            name="Test",
            url="https://example.com",
        )
        assert url_config.success_codes is None


class TestParseSuccessCodes:
    """Tests for _parse_success_codes function."""

    def test_none_returns_none(self) -> None:
        """None input returns None."""
        assert _parse_success_codes(None) is None

    def test_empty_list_returns_none(self) -> None:
        """Empty list returns None."""
        assert _parse_success_codes([]) is None

    def test_parses_single_codes(self) -> None:
        """Parses list of single integer codes."""
        result = _parse_success_codes([200, 201, 404])
        assert result == [200, 201, 404]

    def test_parses_range_codes(self) -> None:
        """Parses range strings into tuples."""
        result = _parse_success_codes(["200-299"])
        assert result == [(200, 299)]

    def test_parses_mixed_codes(self) -> None:
        """Parses mixed single codes and ranges."""
        result = _parse_success_codes([200, "201-299", 400])
        assert result == [200, (201, 299), 400]

    def test_parses_string_single_code(self) -> None:
        """Parses string single code."""
        result = _parse_success_codes(["200"])
        assert result == [200]

    def test_rejects_invalid_code_below_100(self) -> None:
        """Rejects status codes below 100."""
        with pytest.raises(ConfigError, match="must be 100-599"):
            _parse_success_codes([99])

    def test_rejects_invalid_code_above_599(self) -> None:
        """Rejects status codes above 599."""
        with pytest.raises(ConfigError, match="must be 100-599"):
            _parse_success_codes([600])

    def test_rejects_invalid_range_format(self) -> None:
        """Rejects invalid range format."""
        with pytest.raises(ConfigError, match="Invalid range format"):
            _parse_success_codes(["200-299-300"])

    def test_rejects_range_with_invalid_codes(self) -> None:
        """Rejects range with invalid codes."""
        with pytest.raises(ConfigError, match="must be 100-599"):
            _parse_success_codes(["50-200"])

    def test_rejects_inverted_range(self) -> None:
        """Rejects range where start > end."""
        with pytest.raises(ConfigError, match="start must be <= end"):
            _parse_success_codes(["299-200"])

    def test_rejects_non_numeric_range(self) -> None:
        """Rejects non-numeric range values."""
        with pytest.raises(ConfigError, match="Invalid range format"):
            _parse_success_codes(["abc-def"])

    def test_rejects_invalid_entry_type(self) -> None:
        """Rejects invalid entry types."""
        with pytest.raises(ConfigError, match="Invalid success_codes entry"):
            _parse_success_codes([200, 3.14])  # type: ignore[list-item]

    def test_rejects_non_list(self) -> None:
        """Rejects non-list input."""
        with pytest.raises(ConfigError, match="must be a list"):
            _parse_success_codes("200")  # type: ignore[arg-type]


class TestMonitorConfig:
    """Tests for MonitorConfig dataclass."""

    def test_creates_monitor_config_with_defaults(self) -> None:
        """MonitorConfig uses default interval of 60 seconds."""
        monitor = MonitorConfig()
        assert monitor.interval == 60

    def test_creates_monitor_config_with_custom_interval(self) -> None:
        """MonitorConfig accepts custom interval."""
        monitor = MonitorConfig(interval=30)
        assert monitor.interval == 30

    def test_rejects_interval_less_than_10(self) -> None:
        """Interval less than 10 seconds is rejected (Pi 1B+ optimization)."""
        with pytest.raises(ConfigError, match="Monitor interval must be at least 10 seconds"):
            MonitorConfig(interval=5)

    def test_accepts_interval_of_10(self) -> None:
        """Interval of 10 seconds is accepted (minimum for Pi 1B+)."""
        monitor = MonitorConfig(interval=10)
        assert monitor.interval == 10


class TestDatabaseConfig:
    """Tests for DatabaseConfig dataclass."""

    def test_creates_database_config_with_defaults(self) -> None:
        """DatabaseConfig uses XDG-compliant default path and retention."""
        from pathlib import Path

        db = DatabaseConfig()
        # Default path is ~/.local/share/webstatuspi/status.db
        expected_path = str(Path.home() / ".local" / "share" / "webstatuspi" / "status.db")
        assert db.path == expected_path
        assert db.retention_days == 7

    def test_creates_database_config_with_custom_values(self) -> None:
        """DatabaseConfig accepts custom path and retention."""
        db = DatabaseConfig(
            path="/custom/path.db",
            retention_days=14,
        )
        assert db.path == "/custom/path.db"
        assert db.retention_days == 14

    def test_rejects_retention_days_less_than_1(self) -> None:
        """Retention days less than 1 is rejected."""
        with pytest.raises(ConfigError, match="retention_days must be at least 1"):
            DatabaseConfig(retention_days=0)

    def test_accepts_retention_days_of_1(self) -> None:
        """Retention days of 1 is accepted."""
        db = DatabaseConfig(retention_days=1)
        assert db.retention_days == 1


class TestDisplayConfig:
    """Tests for DisplayConfig dataclass."""

    def test_creates_display_config_with_defaults(self) -> None:
        """DisplayConfig uses default values."""
        display = DisplayConfig()
        assert display.enabled is True
        assert display.cycle_interval == 5

    def test_creates_display_config_with_custom_values(self) -> None:
        """DisplayConfig accepts custom values."""
        display = DisplayConfig(enabled=False, cycle_interval=10)
        assert display.enabled is False
        assert display.cycle_interval == 10

    def test_rejects_cycle_interval_less_than_1(self) -> None:
        """Cycle interval less than 1 second is rejected."""
        with pytest.raises(ConfigError, match="cycle_interval must be at least 1 second"):
            DisplayConfig(cycle_interval=0)

    def test_accepts_cycle_interval_of_1(self) -> None:
        """Cycle interval of 1 second is accepted."""
        display = DisplayConfig(cycle_interval=1)
        assert display.cycle_interval == 1


class TestApiConfig:
    """Tests for ApiConfig dataclass."""

    def test_creates_api_config_with_defaults(self) -> None:
        """ApiConfig uses default values."""
        api = ApiConfig()
        assert api.enabled is True
        assert api.port == 8080

    def test_creates_api_config_with_custom_values(self) -> None:
        """ApiConfig accepts custom values."""
        api = ApiConfig(enabled=False, port=9000)
        assert api.enabled is False
        assert api.port == 9000

    def test_rejects_port_less_than_1(self) -> None:
        """Port less than 1 is rejected."""
        with pytest.raises(ConfigError, match="API port must be between 1 and 65535"):
            ApiConfig(port=0)

    def test_rejects_port_greater_than_65535(self) -> None:
        """Port greater than 65535 is rejected."""
        with pytest.raises(ConfigError, match="API port must be between 1 and 65535"):
            ApiConfig(port=65536)

    def test_accepts_port_of_1(self) -> None:
        """Port 1 is accepted."""
        api = ApiConfig(port=1)
        assert api.port == 1

    def test_accepts_port_of_65535(self) -> None:
        """Port 65535 is accepted."""
        api = ApiConfig(port=65535)
        assert api.port == 65535


class TestConfig:
    """Tests for main Config dataclass."""

    def test_creates_config_with_single_url(self) -> None:
        """Config can be created with a single URL."""
        url = UrlConfig(name="Test", url="https://example.com")
        config = Config(urls=[url])
        assert len(config.urls) == 1
        assert config.urls[0].name == "Test"

    def test_creates_config_with_multiple_urls(self) -> None:
        """Config can be created with multiple URLs."""
        urls = [
            UrlConfig(name="Test1", url="https://example1.com"),
            UrlConfig(name="Test2", url="https://example2.com"),
        ]
        config = Config(urls=urls)
        assert len(config.urls) == 2

    def test_uses_default_configs_for_sections(self) -> None:
        """Config uses default values for optional sections."""
        url = UrlConfig(name="Test", url="https://example.com")
        config = Config(urls=[url])
        assert config.monitor.interval == 60
        assert config.database.retention_days == 7
        assert config.api.port == 8080

    def test_rejects_empty_urls_list(self) -> None:
        """Config with no URLs is rejected."""
        with pytest.raises(ConfigError, match="At least one URL must be configured"):
            Config(urls=[])

    def test_rejects_duplicate_url_names(self) -> None:
        """Config with duplicate URL names is rejected."""
        urls = [
            UrlConfig(name="Test", url="https://example1.com"),
            UrlConfig(name="Test", url="https://example2.com"),
        ]
        with pytest.raises(ConfigError, match="Duplicate URL names found"):
            Config(urls=urls)

    def test_allows_multiple_duplicate_names_to_be_detected(self) -> None:
        """Error message lists all duplicate names when multiple exist."""
        urls = [
            UrlConfig(name="Dup1", url="https://example1.com"),
            UrlConfig(name="Dup1", url="https://example2.com"),
            UrlConfig(name="Dup2", url="https://example3.com"),
            UrlConfig(name="Dup2", url="https://example4.com"),
        ]
        with pytest.raises(ConfigError, match="Duplicate URL names found"):
            Config(urls=urls)


class TestLoadConfig:
    """Tests for load_config function."""

    def test_loads_valid_config_from_file(
        self,
        config_dir: Path,
        valid_config_content: str,
    ) -> None:
        """Valid configuration file is loaded successfully."""
        config_file = config_dir / "config.yaml"
        config_file.write_text(valid_config_content)

        config = load_config(str(config_file))

        assert len(config.urls) == 2
        assert config.urls[0].name == "Google"
        assert config.urls[1].name == "GitHub"
        assert config.monitor.interval == 60
        assert config.database.retention_days == 7
        assert config.api.port == 8080

    def test_raises_error_for_missing_file(self, config_dir: Path) -> None:
        """ConfigError is raised when file doesn't exist."""
        missing_file = config_dir / "nonexistent.yaml"
        with pytest.raises(ConfigError, match="Configuration file not found"):
            load_config(str(missing_file))

    def test_raises_error_for_empty_file(self, config_dir: Path) -> None:
        """ConfigError is raised for empty configuration file."""
        config_file = config_dir / "empty.yaml"
        config_file.write_text("")

        with pytest.raises(ConfigError, match="Configuration file is empty"):
            load_config(str(config_file))

    def test_raises_error_for_invalid_yaml(self, config_dir: Path) -> None:
        """ConfigError is raised for invalid YAML syntax."""
        config_file = config_dir / "invalid.yaml"
        config_file.write_text("invalid: yaml: syntax: ][")

        with pytest.raises(ConfigError, match="Failed to parse YAML configuration"):
            load_config(str(config_file))

    def test_raises_error_when_config_is_not_dict(self, config_dir: Path) -> None:
        """ConfigError is raised when configuration is not a dictionary."""
        config_file = config_dir / "notdict.yaml"
        config_file.write_text("- item1\n- item2")

        with pytest.raises(ConfigError, match="Configuration must be a YAML dictionary"):
            load_config(str(config_file))

    def test_raises_error_when_urls_section_missing(self, config_dir: Path) -> None:
        """ConfigError is raised when 'urls' section is missing."""
        config_file = config_dir / "no_urls.yaml"
        config_file.write_text("monitor:\n  interval: 60")

        with pytest.raises(ConfigError, match="must contain 'urls' section"):
            load_config(str(config_file))

    def test_raises_error_when_urls_is_not_list(self, config_dir: Path) -> None:
        """ConfigError is raised when 'urls' is not a list."""
        config_file = config_dir / "urls_not_list.yaml"
        config_file.write_text("urls:\n  name: Test")

        with pytest.raises(ConfigError, match="'urls' must be a list"):
            load_config(str(config_file))

    def test_raises_error_when_url_entry_is_not_dict(self, config_dir: Path) -> None:
        """ConfigError is raised when URL entry is not a dictionary."""
        config_file = config_dir / "url_entry_invalid.yaml"
        config_file.write_text("urls:\n  - https://example.com")

        with pytest.raises(ConfigError, match="URL entry 0 must be a dictionary"):
            load_config(str(config_file))

    def test_raises_error_when_url_missing_name(self, config_dir: Path) -> None:
        """ConfigError is raised when URL entry is missing 'name'."""
        config_file = config_dir / "url_no_name.yaml"
        config_file.write_text("urls:\n  - url: https://example.com")

        with pytest.raises(ConfigError, match="URL entry 0 is missing 'name' field"):
            load_config(str(config_file))

    def test_raises_error_when_url_missing_url_field(self, config_dir: Path) -> None:
        """ConfigError is raised when URL entry is missing 'url' field."""
        config_file = config_dir / "url_no_url.yaml"
        config_file.write_text("urls:\n  - name: Test")

        with pytest.raises(ConfigError, match="URL entry 0 is missing 'url' field"):
            load_config(str(config_file))

    def test_loads_config_with_defaults_for_optional_sections(
        self,
        config_dir: Path,
    ) -> None:
        """Config with only required sections uses defaults for optional ones."""
        config_file = config_dir / "minimal.yaml"
        config_file.write_text("urls:\n  - name: Test\n    url: https://example.com")

        config = load_config(str(config_file))

        assert config.monitor.interval == 60
        assert config.database.retention_days == 7
        assert config.api.port == 8080

    def test_loads_config_with_custom_timeouts(self, config_dir: Path) -> None:
        """URL timeout values are parsed correctly."""
        config_file = config_dir / "custom_timeout.yaml"
        config_file.write_text(
            "urls:\n"
            "  - name: Fast\n"
            "    url: https://example1.com\n"
            "    timeout: 5\n"
            "  - name: Slow\n"
            "    url: https://example2.com\n"
            "    timeout: 30"
        )

        config = load_config(str(config_file))

        assert config.urls[0].timeout == 5
        assert config.urls[1].timeout == 30

    def test_raises_error_for_invalid_url_in_loaded_config(
        self,
        config_dir: Path,
    ) -> None:
        """ConfigError is raised for invalid URL in loaded configuration."""
        config_file = config_dir / "invalid_url.yaml"
        config_file.write_text("urls:\n  - name: Invalid\n    url: not-a-url")

        with pytest.raises(ConfigError, match="must start with http"):
            load_config(str(config_file))

    def test_raises_error_for_invalid_url_name_in_loaded_config(
        self,
        config_dir: Path,
    ) -> None:
        """ConfigError is raised for invalid URL name in loaded configuration."""
        config_file = config_dir / "invalid_name.yaml"
        config_file.write_text("urls:\n  - name: TooLongNameExceedsLimit\n    url: https://example.com")

        with pytest.raises(ConfigError, match="exceeds 10 characters"):
            load_config(str(config_file))


class TestEnvironmentVariableOverrides:
    """Tests for environment variable override functionality."""

    def test_overrides_monitor_interval(self, config_dir: Path, monkeypatch) -> None:
        """WEBSTATUSPI_MONITOR_INTERVAL env var overrides interval."""
        config_file = config_dir / "config.yaml"
        config_file.write_text("urls:\n  - name: Test\n    url: https://example.com\nmonitor:\n  interval: 60")

        monkeypatch.setenv("WEBSTATUSPI_MONITOR_INTERVAL", "30")
        config = load_config(str(config_file))

        assert config.monitor.interval == 30

    def test_overrides_api_port(self, config_dir: Path, monkeypatch) -> None:
        """WEBSTATUSPI_API_PORT env var overrides port."""
        config_file = config_dir / "config.yaml"
        config_file.write_text("urls:\n  - name: Test\n    url: https://example.com")

        monkeypatch.setenv("WEBSTATUSPI_API_PORT", "9000")
        config = load_config(str(config_file))

        assert config.api.port == 9000

    def test_overrides_api_enabled(self, config_dir: Path, monkeypatch) -> None:
        """WEBSTATUSPI_API_ENABLED env var overrides enabled flag."""
        config_file = config_dir / "config.yaml"
        config_file.write_text("urls:\n  - name: Test\n    url: https://example.com\napi:\n  enabled: true")

        monkeypatch.setenv("WEBSTATUSPI_API_ENABLED", "false")
        config = load_config(str(config_file))

        assert config.api.enabled is False

    def test_api_enabled_accepts_true_values(
        self,
        config_dir: Path,
        monkeypatch,
    ) -> None:
        """WEBSTATUSPI_API_ENABLED accepts various true values."""
        config_file = config_dir / "config.yaml"
        config_file.write_text("urls:\n  - name: Test\n    url: https://example.com")

        for true_value in ["true", "True", "TRUE", "1", "yes", "YES"]:
            monkeypatch.setenv("WEBSTATUSPI_API_ENABLED", true_value)
            config = load_config(str(config_file))
            assert config.api.enabled is True, f"Failed for value: {true_value}"

    def test_api_enabled_rejects_false_values(
        self,
        config_dir: Path,
        monkeypatch,
    ) -> None:
        """WEBSTATUSPI_API_ENABLED treats other values as false."""
        config_file = config_dir / "config.yaml"
        config_file.write_text("urls:\n  - name: Test\n    url: https://example.com")

        for false_value in ["false", "False", "0", "no", "anything"]:
            monkeypatch.setenv("WEBSTATUSPI_API_ENABLED", false_value)
            config = load_config(str(config_file))
            assert config.api.enabled is False, f"Failed for value: {false_value}"

    def test_overrides_database_path(self, config_dir: Path, monkeypatch) -> None:
        """WEBSTATUSPI_DB_PATH env var overrides database path."""
        config_file = config_dir / "config.yaml"
        config_file.write_text("urls:\n  - name: Test\n    url: https://example.com")

        monkeypatch.setenv("WEBSTATUSPI_DB_PATH", "/custom/db.sqlite")
        config = load_config(str(config_file))

        assert config.database.path == "/custom/db.sqlite"

    def test_overrides_database_retention_days(
        self,
        config_dir: Path,
        monkeypatch,
    ) -> None:
        """WEBSTATUSPI_DB_RETENTION_DAYS env var overrides retention days."""
        config_file = config_dir / "config.yaml"
        config_file.write_text("urls:\n  - name: Test\n    url: https://example.com")

        monkeypatch.setenv("WEBSTATUSPI_DB_RETENTION_DAYS", "14")
        config = load_config(str(config_file))

        assert config.database.retention_days == 14

    def test_multiple_env_overrides_applied_together(
        self,
        config_dir: Path,
        monkeypatch,
    ) -> None:
        """Multiple environment variable overrides are applied together."""
        config_file = config_dir / "config.yaml"
        config_file.write_text("urls:\n  - name: Test\n    url: https://example.com")

        monkeypatch.setenv("WEBSTATUSPI_MONITOR_INTERVAL", "45")
        monkeypatch.setenv("WEBSTATUSPI_API_PORT", "8888")
        monkeypatch.setenv("WEBSTATUSPI_DB_RETENTION_DAYS", "30")

        config = load_config(str(config_file))

        assert config.monitor.interval == 45
        assert config.api.port == 8888
        assert config.database.retention_days == 30

    def test_env_overrides_create_missing_sections(
        self,
        config_dir: Path,
        monkeypatch,
    ) -> None:
        """Environment variables can override config when sections don't exist."""
        config_file = config_dir / "minimal.yaml"
        # Config with no monitor, api, or database sections
        config_file.write_text("urls:\n  - name: Test\n    url: https://example.com")

        monkeypatch.setenv("WEBSTATUSPI_MONITOR_INTERVAL", "120")
        monkeypatch.setenv("WEBSTATUSPI_API_PORT", "7777")

        config = load_config(str(config_file))

        assert config.monitor.interval == 120
        assert config.api.port == 7777
