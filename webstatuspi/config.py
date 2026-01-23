"""Configuration loader with type-safe dataclasses."""

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


class ConfigError(Exception):
    """Raised when configuration is invalid or cannot be loaded."""

    pass


# Minimum interval between checks in seconds.
# Lower values cause excessive CPU/IO on resource-constrained devices like Pi 1B+.
MIN_MONITOR_INTERVAL = 10


@dataclass(frozen=True)
class MonitorConfig:
    """Configuration for the monitor loop."""

    interval: int = 60  # seconds between check cycles
    ssl_warning_days: int = 30  # days before expiration to warn about SSL certificates
    ssl_cache_seconds: int = 3600  # cache SSL cert info for 1 hour (reduces SSL handshakes)
    default_user_agent: str = "WebStatusPi/0.1"  # default User-Agent header for HTTP requests

    def __post_init__(self) -> None:
        if self.interval < MIN_MONITOR_INTERVAL:
            raise ConfigError(
                f"Monitor interval must be at least {MIN_MONITOR_INTERVAL} seconds "
                f"(got {self.interval}). Lower values cause CPU thrashing on Pi 1B+."
            )
        if self.ssl_warning_days < 0:
            raise ConfigError(f"SSL warning days must be non-negative (got {self.ssl_warning_days})")
        if self.ssl_cache_seconds < 0:
            raise ConfigError(f"SSL cache seconds must be non-negative (got {self.ssl_cache_seconds})")
        if not self.default_user_agent:
            raise ConfigError("Default User-Agent cannot be empty")


def _parse_success_codes(codes: list | None) -> list[int | tuple[int, int]] | None:
    """Parse success_codes into a normalized format.

    Args:
        codes: List of codes (int) or ranges (str like "200-299")

    Returns:
        List of ints and (start, end) tuples, or None if not specified.

    Raises:
        ConfigError: If codes are invalid.
    """
    if codes is None:
        return None

    if not isinstance(codes, list):
        raise ConfigError("success_codes must be a list")

    parsed: list[int | tuple[int, int]] = []
    for code in codes:
        if isinstance(code, int):
            if not (100 <= code <= 599):
                raise ConfigError(f"Invalid HTTP status code: {code} (must be 100-599)")
            parsed.append(code)
        elif isinstance(code, str):
            if "-" in code:
                try:
                    parts = code.split("-")
                    if len(parts) != 2:
                        raise ConfigError(f"Invalid range format: {code}")
                    start, end = int(parts[0]), int(parts[1])
                    if not (100 <= start <= 599) or not (100 <= end <= 599):
                        raise ConfigError(f"Invalid HTTP status code range: {code} (codes must be 100-599)")
                    if start > end:
                        raise ConfigError(f"Invalid range: {code} (start must be <= end)")
                    parsed.append((start, end))
                except ValueError:
                    raise ConfigError(f"Invalid range format: {code}")
            else:
                try:
                    code_int = int(code)
                    if not (100 <= code_int <= 599):
                        raise ConfigError(f"Invalid HTTP status code: {code} (must be 100-599)")
                    parsed.append(code_int)
                except ValueError:
                    raise ConfigError(f"Invalid status code format: {code}")
        else:
            raise ConfigError(f"Invalid success_codes entry: {code}")

    return parsed if parsed else None


@dataclass(frozen=True)
class UrlConfig:
    """Configuration for a single URL to monitor.

    Optional content validation:
    - keyword: Check if response body contains this string (case-sensitive)
    - json_path: Check if JSON response has expected value at this path (e.g., "status.healthy")

    Optional success codes:
    - success_codes: Custom HTTP status codes that indicate success (default: 200-399)

    SSL certificate monitoring:
    - verify_ssl: Whether to check SSL certificate info (default: True for HTTPS URLs).
                  Set to False to skip SSL cert checks and reduce latency on slow hardware.

    Latency alerting:
    - latency_threshold_ms: Alert if response time exceeds this threshold (milliseconds).
    - latency_consecutive_checks: Number of consecutive checks that must exceed threshold to trigger alert (default: 3).

    Custom User-Agent:
    - user_agent: Override the default User-Agent header for this URL. Useful for bypassing WAFs.
    """

    name: str
    url: str
    timeout: int = 10
    keyword: str | None = None
    json_path: str | None = None
    success_codes: list[int | tuple[int, int]] | None = None
    verify_ssl: bool = True
    latency_threshold_ms: int | None = None
    latency_consecutive_checks: int = 3
    user_agent: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ConfigError("URL name cannot be empty")
        if len(self.name) > 10:
            raise ConfigError(f"URL name '{self.name}' exceeds 10 characters (OLED display limit)")
        if not self.url:
            raise ConfigError(f"URL cannot be empty for '{self.name}'")
        if not self.url.startswith(("http://", "https://")):
            raise ConfigError(f"URL must start with http:// or https:// for '{self.name}'")
        if self.timeout < 1:
            raise ConfigError(f"Timeout must be at least 1 second for '{self.name}'")
        if self.latency_threshold_ms is not None and self.latency_threshold_ms < 1:
            raise ConfigError(f"Latency threshold must be at least 1ms for '{self.name}'")
        if self.latency_consecutive_checks < 1:
            raise ConfigError(f"Latency consecutive checks must be at least 1 for '{self.name}'")


@dataclass(frozen=True)
class TcpConfig:
    """Configuration for a TCP port to monitor.

    Used for monitoring non-HTTP services like databases, caches, and custom services.
    """

    name: str
    host: str
    port: int
    timeout: int = 10

    def __post_init__(self) -> None:
        if not self.name:
            raise ConfigError("TCP name cannot be empty")
        if len(self.name) > 10:
            raise ConfigError(f"TCP name '{self.name}' exceeds 10 characters (OLED display limit)")
        if not self.host:
            raise ConfigError(f"TCP host cannot be empty for '{self.name}'")
        if not (1 <= self.port <= 65535):
            raise ConfigError(f"TCP port must be between 1 and 65535 for '{self.name}'")
        if self.timeout < 1:
            raise ConfigError(f"Timeout must be at least 1 second for '{self.name}'")

    @property
    def url(self) -> str:
        """Return a URL-like string for API consistency."""
        return f"tcp://{self.host}:{self.port}"


# Valid DNS record types
DNS_RECORD_TYPES = ("A", "AAAA")


@dataclass(frozen=True)
class DnsConfig:
    """Configuration for a DNS resolution to monitor.

    Used for monitoring DNS resolution of domain names.
    Supports A (IPv4) and AAAA (IPv6) record types.
    """

    name: str
    host: str
    record_type: str = "A"  # A or AAAA
    expected_ip: str | None = None  # Optional: verify resolved IP matches
    timeout: int = 10

    def __post_init__(self) -> None:
        if not self.name:
            raise ConfigError("DNS name cannot be empty")
        if len(self.name) > 10:
            raise ConfigError(f"DNS name '{self.name}' exceeds 10 characters (OLED display limit)")
        if not self.host:
            raise ConfigError(f"DNS host cannot be empty for '{self.name}'")
        if self.record_type not in DNS_RECORD_TYPES:
            raise ConfigError(
                f"Invalid DNS record_type '{self.record_type}' for '{self.name}'. Must be one of: {DNS_RECORD_TYPES}"
            )
        if self.timeout < 1:
            raise ConfigError(f"Timeout must be at least 1 second for '{self.name}'")

    @property
    def url(self) -> str:
        """Return a URL-like string for API consistency."""
        return f"dns://{self.host}"


# Union type for all target configurations
TargetConfig = UrlConfig | TcpConfig | DnsConfig


def _get_default_db_path() -> str:
    """Get the default database path using XDG-compliant directory.

    Returns ~/.local/share/webstatuspi/status.db which is the standard
    location for user-specific data files on Linux/macOS.
    """
    home = Path.home()
    return str(home / ".local" / "share" / "webstatuspi" / "status.db")


# Default database path (XDG-compliant user data directory)
DEFAULT_DB_PATH = _get_default_db_path()


@dataclass(frozen=True)
class DatabaseConfig:
    """Configuration for SQLite database."""

    path: str = DEFAULT_DB_PATH
    retention_days: int = 7

    def __post_init__(self) -> None:
        if self.retention_days < 1:
            raise ConfigError("Database retention_days must be at least 1")


@dataclass(frozen=True)
class DisplayConfig:
    """Configuration for OLED display (future feature)."""

    enabled: bool = True
    cycle_interval: int = 5

    def __post_init__(self) -> None:
        if self.cycle_interval < 1:
            raise ConfigError("Display cycle_interval must be at least 1 second")


@dataclass(frozen=True)
class ApiConfig:
    """Configuration for JSON API server."""

    enabled: bool = True
    port: int = 8080
    reset_token: str | None = None  # Required for DELETE /reset when set

    def __post_init__(self) -> None:
        if self.port < 1 or self.port > 65535:
            raise ConfigError(f"API port must be between 1 and 65535, got {self.port}")


@dataclass(frozen=True)
class WebhookConfig:
    """Configuration for a single webhook alert."""

    url: str
    enabled: bool = True
    on_failure: bool = True  # Send alert when URL goes DOWN
    on_recovery: bool = True  # Send alert when URL comes back UP
    cooldown_seconds: int = 300  # Minimum time between alerts for same URL

    def __post_init__(self) -> None:
        if not self.url:
            raise ConfigError("Webhook URL cannot be empty")
        if not self.url.startswith(("http://", "https://")):
            raise ConfigError(f"Webhook URL must start with http:// or https://, got '{self.url}'")
        if self.cooldown_seconds < 0:
            raise ConfigError(f"Webhook cooldown_seconds must be non-negative, got {self.cooldown_seconds}")
        if not self.on_failure and not self.on_recovery:
            raise ConfigError("Webhook must have at least one of 'on_failure' or 'on_recovery' enabled")


@dataclass(frozen=True)
class HeartbeatConfig:
    """Configuration for heartbeat monitoring (Dead Man's Snitch style)."""

    enabled: bool = False
    url: str = ""
    interval_seconds: int = 300
    timeout_seconds: int = 10

    def __post_init__(self) -> None:
        if self.enabled:
            if not self.url:
                raise ConfigError("Heartbeat URL is required when heartbeat is enabled")
            if not self.url.startswith(("http://", "https://")):
                raise ConfigError(f"Heartbeat URL must start with http:// or https://, got '{self.url}'")
            if self.interval_seconds < 1:
                raise ConfigError(f"Heartbeat interval must be at least 1 second, got {self.interval_seconds}")
            if self.timeout_seconds < 1:
                raise ConfigError(f"Heartbeat timeout must be at least 1 second, got {self.timeout_seconds}")


@dataclass(frozen=True)
class AlertsConfig:
    """Configuration for alert mechanisms."""

    webhooks: list[WebhookConfig] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.webhooks, list):
            raise ConfigError("Webhooks must be a list")


@dataclass(frozen=True)
class Config:
    """Main configuration container."""

    urls: list[UrlConfig]
    tcp: list[TcpConfig] = field(default_factory=list)
    dns: list[DnsConfig] = field(default_factory=list)
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    alerts: AlertsConfig = field(default_factory=AlertsConfig)
    heartbeat: HeartbeatConfig = field(default_factory=HeartbeatConfig)

    def __post_init__(self) -> None:
        if not self.urls and not self.tcp and not self.dns:
            raise ConfigError("At least one URL, TCP, or DNS target must be configured")
        # Check for duplicate names across all target types
        names = [url.name for url in self.urls] + [tcp.name for tcp in self.tcp] + [dns.name for dns in self.dns]
        duplicates = [name for name in names if names.count(name) > 1]
        if duplicates:
            raise ConfigError(f"Duplicate target names found: {set(duplicates)}")

    @property
    def all_targets(self) -> list[TargetConfig]:
        """Return all monitoring targets (URLs, TCP, and DNS endpoints)."""
        return list(self.urls) + list(self.tcp) + list(self.dns)


def _parse_url_config(data: dict, index: int) -> UrlConfig:
    """Parse a single URL configuration entry."""
    if not isinstance(data, dict):
        raise ConfigError(f"URL entry {index} must be a dictionary")

    name = data.get("name")
    url = data.get("url")

    if name is None:
        raise ConfigError(f"URL entry {index} is missing 'name' field")
    if url is None:
        raise ConfigError(f"URL entry {index} is missing 'url' field")

    keyword = data.get("keyword")
    json_path = data.get("json_path")
    success_codes_raw = data.get("success_codes")
    success_codes = _parse_success_codes(success_codes_raw)

    latency_threshold_ms = data.get("latency_threshold_ms")
    latency_consecutive_checks = data.get("latency_consecutive_checks", 3)

    return UrlConfig(
        name=str(name),
        url=str(url),
        timeout=int(data.get("timeout", 10)),
        keyword=str(keyword) if keyword is not None else None,
        json_path=str(json_path) if json_path is not None else None,
        success_codes=success_codes,
        verify_ssl=bool(data.get("verify_ssl", True)),
        latency_threshold_ms=int(latency_threshold_ms) if latency_threshold_ms is not None else None,
        latency_consecutive_checks=int(latency_consecutive_checks),
    )


def _parse_tcp_config(data: dict, index: int) -> TcpConfig:
    """Parse a single TCP configuration entry."""
    if not isinstance(data, dict):
        raise ConfigError(f"TCP entry {index} must be a dictionary")

    name = data.get("name")
    host = data.get("host")
    port = data.get("port")

    if name is None:
        raise ConfigError(f"TCP entry {index} is missing 'name' field")
    if host is None:
        raise ConfigError(f"TCP entry {index} is missing 'host' field")
    if port is None:
        raise ConfigError(f"TCP entry {index} is missing 'port' field")

    return TcpConfig(
        name=str(name),
        host=str(host),
        port=int(port),
        timeout=int(data.get("timeout", 10)),
    )


def _parse_dns_config(data: dict, index: int) -> DnsConfig:
    """Parse a single DNS configuration entry."""
    if not isinstance(data, dict):
        raise ConfigError(f"DNS entry {index} must be a dictionary")

    name = data.get("name")
    host = data.get("host")

    if name is None:
        raise ConfigError(f"DNS entry {index} is missing 'name' field")
    if host is None:
        raise ConfigError(f"DNS entry {index} is missing 'host' field")

    expected_ip = data.get("expected_ip")

    return DnsConfig(
        name=str(name),
        host=str(host),
        record_type=str(data.get("record_type", "A")),
        expected_ip=str(expected_ip) if expected_ip is not None else None,
        timeout=int(data.get("timeout", 10)),
    )


def _parse_monitor_config(data: dict | None) -> MonitorConfig:
    """Parse monitor configuration section."""
    if data is None:
        return MonitorConfig()
    if not isinstance(data, dict):
        raise ConfigError("'monitor' section must be a dictionary")

    return MonitorConfig(
        interval=int(data.get("interval", 60)),
        ssl_warning_days=int(data.get("ssl_warning_days", 30)),
        ssl_cache_seconds=int(data.get("ssl_cache_seconds", 3600)),
    )


def _parse_database_config(data: dict | None) -> DatabaseConfig:
    """Parse database configuration section."""
    if data is None:
        return DatabaseConfig()
    if not isinstance(data, dict):
        raise ConfigError("'database' section must be a dictionary")

    return DatabaseConfig(
        path=str(data.get("path", DEFAULT_DB_PATH)),
        retention_days=int(data.get("retention_days", 7)),
    )


def _parse_display_config(data: dict | None) -> DisplayConfig:
    """Parse display configuration section."""
    if data is None:
        return DisplayConfig()
    if not isinstance(data, dict):
        raise ConfigError("'display' section must be a dictionary")

    return DisplayConfig(
        enabled=bool(data.get("enabled", True)),
        cycle_interval=int(data.get("cycle_interval", 5)),
    )


def _parse_api_config(data: dict | None) -> ApiConfig:
    """Parse API configuration section."""
    if data is None:
        return ApiConfig()
    if not isinstance(data, dict):
        raise ConfigError("'api' section must be a dictionary")

    reset_token = data.get("reset_token")
    if reset_token is not None:
        reset_token = str(reset_token)

    return ApiConfig(
        enabled=bool(data.get("enabled", True)),
        port=int(data.get("port", 8080)),
        reset_token=reset_token,
    )


def _parse_webhook_config(data: dict, index: int) -> WebhookConfig:
    """Parse a single webhook configuration entry."""
    if not isinstance(data, dict):
        raise ConfigError(f"Webhook entry {index} must be a dictionary")

    url = data.get("url")
    if url is None:
        raise ConfigError(f"Webhook entry {index} is missing 'url' field")

    return WebhookConfig(
        url=str(url),
        enabled=bool(data.get("enabled", True)),
        on_failure=bool(data.get("on_failure", True)),
        on_recovery=bool(data.get("on_recovery", True)),
        cooldown_seconds=int(data.get("cooldown_seconds", 300)),
    )


def _parse_alerts_config(data: dict | None) -> AlertsConfig:
    """Parse alerts configuration section."""
    if data is None:
        return AlertsConfig()
    if not isinstance(data, dict):
        raise ConfigError("'alerts' section must be a dictionary")

    webhooks_data = data.get("webhooks", [])
    if not isinstance(webhooks_data, list):
        raise ConfigError("'alerts.webhooks' must be a list")

    webhooks = [_parse_webhook_config(webhook_data, i) for i, webhook_data in enumerate(webhooks_data)]

    return AlertsConfig(webhooks=webhooks)


def _parse_heartbeat_config(data: dict | None) -> HeartbeatConfig:
    """Parse heartbeat configuration section."""
    if data is None:
        return HeartbeatConfig()
    if not isinstance(data, dict):
        raise ConfigError("'heartbeat' section must be a dictionary")

    return HeartbeatConfig(
        enabled=data.get("enabled", False),
        url=data.get("url", ""),
        interval_seconds=data.get("interval_seconds", 300),
        timeout_seconds=data.get("timeout_seconds", 10),
    )


def _apply_env_overrides(config_data: dict) -> dict:
    """Apply environment variable overrides to configuration.

    Supported overrides:
    - WEBSTATUSPI_MONITOR_INTERVAL: Override monitor.interval
    - WEBSTATUSPI_API_PORT: Override api.port
    - WEBSTATUSPI_API_ENABLED: Override api.enabled (true/false)
    - WEBSTATUSPI_API_RESET_TOKEN: Override api.reset_token
    - WEBSTATUSPI_DB_PATH: Override database.path
    - WEBSTATUSPI_DB_RETENTION_DAYS: Override database.retention_days
    """
    if "monitor" not in config_data:
        config_data["monitor"] = {}
    if "api" not in config_data:
        config_data["api"] = {}
    if "database" not in config_data:
        config_data["database"] = {}

    monitor_interval = os.environ.get("WEBSTATUSPI_MONITOR_INTERVAL")
    if monitor_interval is not None:
        config_data["monitor"]["interval"] = int(monitor_interval)

    api_port = os.environ.get("WEBSTATUSPI_API_PORT")
    if api_port is not None:
        config_data["api"]["port"] = int(api_port)

    api_enabled = os.environ.get("WEBSTATUSPI_API_ENABLED")
    if api_enabled is not None:
        config_data["api"]["enabled"] = api_enabled.lower() in ("true", "1", "yes")

    api_reset_token = os.environ.get("WEBSTATUSPI_API_RESET_TOKEN")
    if api_reset_token is not None:
        config_data["api"]["reset_token"] = api_reset_token

    db_path = os.environ.get("WEBSTATUSPI_DB_PATH")
    if db_path is not None:
        config_data["database"]["path"] = db_path

    db_retention = os.environ.get("WEBSTATUSPI_DB_RETENTION_DAYS")
    if db_retention is not None:
        config_data["database"]["retention_days"] = int(db_retention)

    return config_data


def load_config(config_path: str) -> Config:
    """Load and validate configuration from a YAML file.

    Args:
        config_path: Path to the YAML configuration file.

    Returns:
        Validated Config object.

    Raises:
        ConfigError: If the file cannot be read or configuration is invalid.
    """
    path = Path(config_path)

    if not path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    try:
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Failed to parse YAML configuration: {e}")
    except OSError as e:
        raise ConfigError(f"Failed to read configuration file: {e}")

    if data is None:
        raise ConfigError("Configuration file is empty")

    if not isinstance(data, dict):
        raise ConfigError("Configuration must be a YAML dictionary")

    data = _apply_env_overrides(data)

    urls_data = data.get("urls")
    tcp_data = data.get("tcp")
    dns_data = data.get("dns")

    # At least one of urls, tcp, or dns must be present
    if urls_data is None and tcp_data is None and dns_data is None:
        raise ConfigError("Configuration must contain 'urls', 'tcp', or 'dns' section")

    # Parse URLs (optional if tcp or dns is present)
    urls: list[UrlConfig] = []
    if urls_data is not None:
        if not isinstance(urls_data, list):
            raise ConfigError("'urls' must be a list")
        urls = [_parse_url_config(url_data, i) for i, url_data in enumerate(urls_data)]

    # Parse TCP targets (optional)
    tcp: list[TcpConfig] = []
    if tcp_data is not None:
        if not isinstance(tcp_data, list):
            raise ConfigError("'tcp' must be a list")
        tcp = [_parse_tcp_config(tcp_entry, i) for i, tcp_entry in enumerate(tcp_data)]

    # Parse DNS targets (optional)
    dns: list[DnsConfig] = []
    if dns_data is not None:
        if not isinstance(dns_data, list):
            raise ConfigError("'dns' must be a list")
        dns = [_parse_dns_config(dns_entry, i) for i, dns_entry in enumerate(dns_data)]

    return Config(
        urls=urls,
        tcp=tcp,
        dns=dns,
        monitor=_parse_monitor_config(data.get("monitor")),
        database=_parse_database_config(data.get("database")),
        display=_parse_display_config(data.get("display")),
        api=_parse_api_config(data.get("api")),
        alerts=_parse_alerts_config(data.get("alerts")),
        heartbeat=_parse_heartbeat_config(data.get("heartbeat")),
    )
