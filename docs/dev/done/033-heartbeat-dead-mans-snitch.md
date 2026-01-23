# Task #033: Heartbeat (Dead Man's Snitch)

## Metadata
- **Status**: completed
- **Priority**: P3
- **Slice**: DevOps, Config, Core
- **Created**: 2026-01-23
- **Started**: 2026-01-23
- **Completed**: 2026-01-23
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a system administrator, I want WebStatusPi to send periodic heartbeat pings to an external monitoring service so that I get alerted if the monitoring system itself stops working.

**Acceptance Criteria**:
- [x] Config schema supports heartbeat URL and interval
- [x] Heartbeat ping sent at configured interval
- [x] Heartbeat runs in separate thread to avoid blocking monitor loop
- [x] Failed heartbeat attempts are logged (but don't crash the service)
- [x] Heartbeat is optional and disabled by default
- [x] Unit tests for heartbeat logic (config tests pass)
- [x] Documentation added to config.example.yaml with examples

## Implementation Notes

### Config Schema Addition

```yaml
heartbeat:
  enabled: true
  url: "https://hc-ping.com/your-uuid-here"
  interval_seconds: 300  # 5 minutes
  timeout_seconds: 10
```

### Compatible Services

- **Healthchecks.io** - `https://hc-ping.com/<uuid>`
- **Dead Man's Snitch** - `https://nosnch.in/<token>`
- **Cronitor** - `https://cronitor.link/<monitor-id>`
- **Uptime Robot** - Heartbeat monitors
- **Better Uptime** - Heartbeat monitors
- **Any webhook** - Simple GET request

### Implementation

Create new module `webstatuspi/heartbeat.py`:

```python
"""Heartbeat module for self-monitoring."""

import logging
import threading
import time
from urllib.request import urlopen, Request
from urllib.error import URLError

from webstatuspi.config import HeartbeatConfig

logger = logging.getLogger(__name__)


class Heartbeat:
    """Sends periodic heartbeat pings to external monitoring service."""

    def __init__(self, config: HeartbeatConfig) -> None:
        self.config = config
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start heartbeat thread."""
        if not self.config.enabled:
            logger.info("Heartbeat disabled")
            return

        self._thread = threading.Thread(
            target=self._run,
            name="heartbeat",
            daemon=True
        )
        self._thread.start()
        logger.info(f"Heartbeat started (interval: {self.config.interval_seconds}s)")

    def stop(self) -> None:
        """Stop heartbeat thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _run(self) -> None:
        """Main heartbeat loop."""
        while not self._stop_event.is_set():
            self._send_ping()
            self._stop_event.wait(self.config.interval_seconds)

    def _send_ping(self) -> None:
        """Send a single heartbeat ping."""
        try:
            req = Request(
                self.config.url,
                headers={"User-Agent": "WebStatusPi-Heartbeat/1.0"}
            )
            with urlopen(req, timeout=self.config.timeout_seconds) as resp:
                if resp.status < 400:
                    logger.debug(f"Heartbeat ping successful: {resp.status}")
                else:
                    logger.warning(f"Heartbeat ping returned {resp.status}")
        except URLError as e:
            logger.warning(f"Heartbeat ping failed: {e}")
        except Exception as e:
            logger.error(f"Heartbeat unexpected error: {e}")
```

### Config Changes

Add new dataclass:
```python
@dataclass
class HeartbeatConfig:
    enabled: bool = False
    url: str = ""
    interval_seconds: int = 300
    timeout_seconds: int = 10
```

Add to main Config:
```python
@dataclass
class Config:
    # ... existing fields ...
    heartbeat: HeartbeatConfig = field(default_factory=HeartbeatConfig)
```

### Integration in __main__.py

```python
from webstatuspi.heartbeat import Heartbeat

def main():
    config = load_config()

    # Start heartbeat if configured
    heartbeat = Heartbeat(config.heartbeat)
    heartbeat.start()

    # ... existing monitor/api startup ...

    # On shutdown
    heartbeat.stop()
```

### Security Considerations

- Heartbeat URL validation (SSRF protection) - reuse existing URL validation
- Don't log the full URL (may contain tokens)
- Use HTTPS only

### Example Configurations

```yaml
# Healthchecks.io (free tier available)
heartbeat:
  enabled: true
  url: "https://hc-ping.com/your-uuid"
  interval_seconds: 300

# Dead Man's Snitch
heartbeat:
  enabled: true
  url: "https://nosnch.in/your-token"
  interval_seconds: 900  # 15 minutes

# Self-hosted endpoint
heartbeat:
  enabled: true
  url: "https://your-server.com/heartbeat/webstatuspi"
  interval_seconds: 60
```

## Files to Modify

- `webstatuspi/config.py` - Add HeartbeatConfig dataclass
- `webstatuspi/heartbeat.py` - New module (create)
- `webstatuspi/__main__.py` - Integrate heartbeat start/stop
- `config.example.yaml` - Add heartbeat examples
- `README.md` - Document heartbeat configuration
- `tests/test_heartbeat.py` - New test file (create)
- `tests/test_config.py` - Add tests for heartbeat config

## Dependencies

None - uses stdlib `urllib`

## Follow-up Tasks

- Add heartbeat status to `/health` endpoint
- Add option to include system stats in heartbeat (memory, CPU)

## Progress Log

### 2026-01-23 - Implementation Complete

- ✅ Created `heartbeat.py` module with Heartbeat class
- ✅ Added HeartbeatConfig dataclass with validation (enabled, url, interval, timeout)
- ✅ Added `_parse_heartbeat_config()` function to parse config
- ✅ Integrated heartbeat into main Config dataclass
- ✅ Updated `__init__.py` to start/stop heartbeat with other components
- ✅ Heartbeat runs in daemon thread, stops gracefully on shutdown
- ✅ Failed pings logged as warnings, don't crash the service
- ✅ URL masking for security (sensitive tokens hidden in logs)
- ✅ Added heartbeat examples to config.example.yaml
- ✅ All 399 tests pass

**Implementation approach:**
- Disabled by default (enabled: false)
- Uses threading.Event for interruptible sleep
- Validates URL and intervals when enabled

## Learnings

(empty)
