# Task #016: Webhook Alerts

## Metadata
- **Status**: completed
- **Priority**: P1 - Active
- **Slice**: Core, Config, API
- **Created**: 2026-01-21
- **Started**: 2026-01-21
- **Completed**: 2026-01-21
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a site owner and DevOps engineer, I want to receive instant notifications via webhooks when my monitored URLs fail or recover so that I can respond quickly to outages and integrate with my existing tools (Slack, Discord, Telegram, PagerDuty, etc.).

**Acceptance Criteria**:
- [ ] Config schema supports webhook configuration (url, enabled, on_failure, on_recovery, cooldown_seconds)
- [ ] State change detection tracks URL transitions (UP→DOWN, DOWN→UP) and only alerts on state changes
- [ ] Cooldown mechanism prevents alert spam (configurable per-webhook, default 300s)
- [ ] Webhook POST implementation sends JSON payload with url, name, status, status_code, timestamp, response_time, error details
- [ ] Multiple webhooks supported (array in config) for different destinations
- [ ] Test command `webstatuspi test-alert` to verify webhook configuration works
- [ ] Unit tests for state transition logic and cooldown mechanism
- [ ] Integration test for webhook POST (mocked HTTP)

## Implementation Notes

### Webhook Payload Format

```json
{
  "event": "url_down" | "url_up",
  "url": {
    "name": "APP_ES",
    "url": "https://example.com"
  },
  "status": {
    "code": 503,
    "success": false,
    "response_time_ms": 1234,
    "error": "Service Unavailable",
    "timestamp": "2026-01-21T10:30:00Z"
  },
  "previous_status": "up" | "down"
}
```

### Config Schema Addition

```yaml
alerts:
  webhooks:
    - url: "https://example.com/webhook"
      enabled: true
      on_failure: true      # Send when URL goes DOWN
      on_recovery: true     # Send when URL comes back UP
      cooldown_seconds: 300 # Minimum time between repeat alerts (per URL)

    - url: "https://hooks.slack.com/services/..."
      enabled: true
      on_failure: true
      on_recovery: false    # Only alert on failures
      cooldown_seconds: 600
```

### State Tracking

Need to track previous state per URL to detect transitions:
- Store in memory (dict): `{url_name: last_alert_state}`
- Track last alert timestamp for cooldown: `{url_name: last_alert_time}`
- Only send alert if state changed AND cooldown expired

### Architecture

1. **Alerter Module** (`webstatuspi/alerter.py`)
   - `should_send_alert(url_name, current_status) -> bool`
   - `send_webhook_alert(webhook_config, payload) -> bool`
   - State tracking in memory (no database needed)

2. **Integration Point** (`webstatuspi/monitor.py`)
   - After each check, call alerter with result
   - Non-blocking (don't delay monitoring if webhook fails)

3. **Test Command** (`webstatuspi/__init__.py`)
   - New subcommand: `test-alert`
   - Sends test payload to all configured webhooks
   - Reports success/failure for each

## Files to Modify

**New Files**:
- `webstatuspi/alerter.py` - Alert logic, state tracking, webhook sending
- `tests/test_alerter.py` - Unit tests for alerter module

**Modified Files**:
- `webstatuspi/config.py` - Add AlertConfig and WebhookConfig dataclasses
- `webstatuspi/monitor.py` - Integrate alerter after each check
- `webstatuspi/__init__.py` - Add test-alert CLI command
- `config.example.yaml` - Add alerts section with examples
- `README.md` - Add Alerts section with overview
- `AGENTS.md` - Update if new patterns emerge

## Dependencies

None - uses existing `requests` library for HTTP POST

## Follow-up Tasks

- #017 (Telegram Bot Integration Documentation) - Depends on this task

## Progress Log

- [2026-01-21 00:00] Started task
- [2026-01-21 00:01] Implemented WebhookConfig and AlertConfig dataclasses with validation
- [2026-01-21 00:02] Created alerter.py module with state tracking, cooldown management, and retry logic
- [2026-01-21 00:03] Integrated alerter into monitor via on_check callback
- [2026-01-21 00:04] Added test-alert CLI command for webhook verification
- [2026-01-21 00:05] Created comprehensive test suite (23 tests, all passing)
- [2026-01-21 00:06] Updated config.example.yaml with webhook examples (Slack, Discord, PagerDuty)
- [2026-01-21 00:07] Added webhook alerts documentation to README.md with setup guides
- [2026-01-21 00:08] Task completed - all acceptance criteria met

## Learnings

1. **State tracking pattern**: Using in-memory dictionaries keyed by URL name is efficient and thread-safe with locks
2. **Cooldown mechanism**: Tracking last alert timestamp per URL prevents alert spam effectively
3. **Webhook retry strategy**: Exponential backoff (delay * 2^attempt) is effective for transient failures
4. **Integration point**: The Monitor's on_check callback pattern is perfect for event-driven features
5. **Config validation**: Using frozen dataclasses with __post_init__ provides immutability and fail-fast validation
6. **Test coverage**: 23 tests covering state transitions, filters, cooldowns, retries, and payload structure
