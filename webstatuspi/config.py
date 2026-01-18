"""Configuration loader with type-safe dataclasses."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

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

    def __post_init__(self) -> None:
        if self.interval < MIN_MONITOR_INTERVAL:
            raise ConfigError(
                f"Monitor interval must be at least {MIN_MONITOR_INTERVAL} seconds "
                f"(got {self.interval}). Lower values cause CPU thrashing on Pi 1B+."
            )


@dataclass(frozen=True)
class UrlConfig:
    """Configuration for a single URL to monitor."""
    name: str
    url: str
    timeout: int = 10

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
    reset_token: Optional[str] = None  # Required for DELETE /reset when set

    def __post_init__(self) -> None:
        if self.port < 1 or self.port > 65535:
            raise ConfigError(f"API port must be between 1 and 65535, got {self.port}")


@dataclass(frozen=True)
class Config:
    """Main configuration container."""
    urls: List[UrlConfig]
    monitor: MonitorConfig = field(default_factory=MonitorConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    display: DisplayConfig = field(default_factory=DisplayConfig)
    api: ApiConfig = field(default_factory=ApiConfig)

    def __post_init__(self) -> None:
        if not self.urls:
            raise ConfigError("At least one URL must be configured")
        names = [url.name for url in self.urls]
        duplicates = [name for name in names if names.count(name) > 1]
        if duplicates:
            raise ConfigError(f"Duplicate URL names found: {set(duplicates)}")


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

    return UrlConfig(
        name=str(name),
        url=str(url),
        timeout=int(data.get("timeout", 10)),
    )


def _parse_monitor_config(data: Optional[dict]) -> MonitorConfig:
    """Parse monitor configuration section."""
    if data is None:
        return MonitorConfig()
    if not isinstance(data, dict):
        raise ConfigError("'monitor' section must be a dictionary")

    return MonitorConfig(
        interval=int(data.get("interval", 60)),
    )


def _parse_database_config(data: Optional[dict]) -> DatabaseConfig:
    """Parse database configuration section."""
    if data is None:
        return DatabaseConfig()
    if not isinstance(data, dict):
        raise ConfigError("'database' section must be a dictionary")

    return DatabaseConfig(
        path=str(data.get("path", DEFAULT_DB_PATH)),
        retention_days=int(data.get("retention_days", 7)),
    )


def _parse_display_config(data: Optional[dict]) -> DisplayConfig:
    """Parse display configuration section."""
    if data is None:
        return DisplayConfig()
    if not isinstance(data, dict):
        raise ConfigError("'display' section must be a dictionary")

    return DisplayConfig(
        enabled=bool(data.get("enabled", True)),
        cycle_interval=int(data.get("cycle_interval", 5)),
    )


def _parse_api_config(data: Optional[dict]) -> ApiConfig:
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
        with open(path, "r", encoding="utf-8") as f:
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
    if urls_data is None:
        raise ConfigError("Configuration must contain 'urls' section")
    if not isinstance(urls_data, list):
        raise ConfigError("'urls' must be a list")

    urls = [_parse_url_config(url_data, i) for i, url_data in enumerate(urls_data)]

    return Config(
        urls=urls,
        monitor=_parse_monitor_config(data.get("monitor")),
        database=_parse_database_config(data.get("database")),
        display=_parse_display_config(data.get("display")),
        api=_parse_api_config(data.get("api")),
    )
