# Feature Suggestions for WebStatusπ

This document outlines potential features that could add significant value to WebStatusπ, particularly for public-facing dashboards. Features are prioritized based on their value, implementation complexity, and alignment with the project's constraints (Raspberry Pi 1B+ hardware limitations).

## High-Value Features

### 1. RSS Feed for Status Updates (Priority: P2) ✅ IMPLEMENTED

> **Status**: Implemented in v0.2.0
> - Endpoint: `GET /rss.xml`
> - Configuration: `api.rss.enabled`, `api.rss.title`, `api.rss.max_items`, `api.rss.link`
> - Tests: `tests/test_rss.py`

**Value**: Allows users to subscribe to status changes via RSS readers, enabling automatic notifications when services go down or recover.

**Use Cases**:
- Users subscribe to RSS feed in their reader
- Integration with monitoring tools that consume RSS
- Automated notifications via RSS-to-email services
- Status page aggregators

**Implementation**:
- New endpoint: `GET /rss.xml`
- RSS 2.0 format with status updates
- Include last check time, current status, and brief description
- Lightweight XML generation (stdlib only)

**Configuration**:
```yaml
api:
  rss:
    enabled: true
    title: "WebStatusπ Status Feed"
    description: "Real-time status updates for monitored services"
    max_items: 20  # Number of recent status changes to include
```

**Complexity**: Low  
**Dependencies**: None (stdlib XML generation)

---

### 2. Embeddable Status Badge/Widget (Priority: P2)

**Value**: Allows other websites to embed a visual status indicator, increasing visibility and transparency.

**Use Cases**:
- Embed badge in main website footer
- Show status in documentation sites
- Display in README files (GitHub, GitLab)
- Integration with status page aggregators

**Implementation**:
- Endpoint: `GET /badge.svg` or `GET /badge.png`
- Dynamic image generation showing current status
- Query parameters: `?url=URL_NAME` for specific service, or overall status
- SVG format preferred (scalable, lightweight)

**Example URLs**:
- `https://status.jmlweb.es/badge.svg` - Overall system status
- `https://status.jmlweb.es/badge.svg?url=APP_ES` - Specific service status

**Badge States**:
- Green: All services operational
- Yellow: Some services degraded
- Red: One or more services down
- Gray: Unknown/checking

**Complexity**: Medium  
**Dependencies**: Optional: `Pillow` for PNG generation (SVG can use stdlib)

---

### 3. Email Alerts (SMTP) (Priority: P2) ✅ IMPLEMENTED

> **Status**: Implemented in v0.3.0
> - Configuration: `alerts.smtp.enabled`, `alerts.smtp.host`, `alerts.smtp.port`, etc.
> - Methods: `Alerter._send_email_alert()`, `Alerter.test_smtp()`
> - Tests: `tests/test_alerter.py::TestSmtpAlerts`

**Value**: Alternative to webhooks for notifications, useful when Slack/Discord are not available or for critical alerts.

**Use Cases**:
- Critical service downtime notifications
- Daily/weekly summary reports
- SSL certificate expiration warnings
- Latency degradation alerts

**Implementation**:
- Use stdlib `smtplib` (zero dependencies)
- Support TLS/STARTTLS
- HTML and plain text email formats
- Configurable email templates

**Configuration**:
```yaml
alerts:
  email:
    enabled: true
    smtp_host: "smtp.gmail.com"
    smtp_port: 587
    smtp_user: "alerts@example.com"
    smtp_password: "your-password"  # Or use environment variable
    smtp_tls: true
    from_address: "WebStatusπ <alerts@example.com>"
    to_addresses:
      - "admin@example.com"
      - "ops@example.com"
    on_failure: true
    on_recovery: true
    on_latency_high: true
    cooldown_seconds: 300
```

**Security Notes**:
- Store SMTP credentials in environment variables when possible
- Support OAuth2 for Gmail/Office365 (future enhancement)
- Rate limit email sending to prevent abuse

**Complexity**: Medium  
**Dependencies**: None (stdlib `smtplib`)

---

### 4. Incident Timeline (Priority: P3)

**Value**: Public-facing history of incidents, providing transparency and accountability.

**Use Cases**:
- Users can see historical incidents
- Track resolution times
- Identify patterns in outages
- Build trust through transparency

**Implementation**:
- New database table: `incidents`
- Automatically create incidents when services transition to DOWN
- Mark incidents as resolved when services recover
- Display timeline in dashboard (new section or modal)

**Database Schema**:
```sql
CREATE TABLE incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_name TEXT NOT NULL,
    started_at TEXT NOT NULL,
    resolved_at TEXT,
    status_code INTEGER,
    error_message TEXT,
    duration_seconds INTEGER
);
```

**Dashboard Integration**:
- New "Incidents" section showing recent incidents
- Filter by date range
- Show duration, affected services, resolution time

**Configuration**:
```yaml
incidents:
  enabled: true
  auto_create: true  # Automatically create incidents on status changes
  retention_days: 90  # Keep incident history for 90 days
```

**Complexity**: Medium  
**Dependencies**: None

---

### 5. Dark/Light Mode Toggle with Persistence (Priority: P3)

**Value**: Improves user experience by allowing users to choose their preferred theme and persist the choice.

**Use Cases**:
- Users prefer dark mode for reduced eye strain
- Better visibility in different lighting conditions
- Personal preference

**Implementation**:
- Add theme toggle button in dashboard header
- Store preference in `localStorage`
- Apply theme class to `<body>` element
- CSS variables for easy theme switching

**Features**:
- Toggle button with icon (sun/moon)
- Smooth transition between themes
- Respects system preference on first visit (via `prefers-color-scheme`)
- Persists across page reloads

**Complexity**: Low  
**Dependencies**: None

---

### 6. Data Export (CSV/JSON) (Priority: P3)

**Value**: Enables external analysis, reporting, and integration with other tools.

**Use Cases**:
- Generate reports for stakeholders
- Import data into Excel/Google Sheets
- Analyze trends with external tools
- Backup monitoring data

**Implementation**:
- Endpoint: `GET /export/{name}.csv` or `/export/{name}.json`
- Query parameters for date range: `?from=2026-01-20&to=2026-01-23`
- CSV format: timestamp, status, code, latency, error
- JSON format: array of check objects

**Example**:
```bash
# Export last 7 days as CSV
curl "https://status.jmlweb.es/export/APP_ES.csv?days=7"

# Export specific date range as JSON
curl "https://status.jmlweb.es/export/APP_ES.json?from=2026-01-20&to=2026-01-23"
```

**Configuration**:
```yaml
api:
  export:
    enabled: true
    max_days: 30  # Maximum days of data to export
    formats: ["csv", "json"]
```

**Complexity**: Low  
**Dependencies**: None (stdlib CSV module)

---

### 7. Scheduled Maintenance Windows (Priority: P3)

**Value**: Prevents false alerts during planned maintenance, improving signal-to-noise ratio.

**Use Cases**:
- Planned server maintenance
- Database migrations
- Scheduled deployments
- System updates

**Implementation**:
- Pause monitoring during configured time windows
- Skip alerts during maintenance
- Show maintenance indicator in dashboard
- Log maintenance periods

**Configuration**:
```yaml
maintenance:
  windows:
    - name: "Weekly Maintenance"
      start: "2026-01-25T02:00:00Z"
      end: "2026-01-25T04:00:00Z"
      recurring: "weekly"  # weekly, daily, monthly, or one-time
      affected_urls:
        - "APP_ES"
        - "API_PROD"
    - name: "Database Migration"
      start: "2026-02-01T10:00:00Z"
      end: "2026-02-01T12:00:00Z"
      recurring: false  # One-time maintenance
      affected_urls: ["DB_PROD"]
```

**Dashboard Behavior**:
- Show "Under Maintenance" badge on affected services
- Display maintenance schedule in dashboard
- Skip webhook/email alerts during maintenance
- Continue monitoring but mark as "maintenance mode"

**Complexity**: Medium  
**Dependencies**: None

---

### 8. System-Wide Aggregated Statistics (Priority: P3)

**Value**: Provides high-level overview of system health, useful for quick status assessment.

**Use Cases**:
- Quick health check
- Executive dashboards
- System performance overview
- Trend analysis

**Implementation**:
- New endpoint: `GET /stats` or extend `/status` with `summary` section
- Calculate aggregate metrics across all services
- Include: average uptime, average response time, total checks, system uptime

**Response Format**:
```json
{
  "summary": {
    "total_services": 5,
    "services_up": 4,
    "services_down": 1,
    "average_uptime_24h": 99.2,
    "average_response_time_24h": 145.5,
    "total_checks_24h": 7200,
    "system_uptime_days": 45
  },
  "trends": {
    "uptime_trend": "improving",  # improving, stable, degrading
    "latency_trend": "stable"
  }
}
```

**Dashboard Integration**:
- Add "System Overview" card
- Show key metrics at a glance
- Link to detailed breakdown

**Complexity**: Low  
**Dependencies**: None

---

## Implementation Priority

### Phase 1 (High Impact, Low Complexity)
1. **RSS Feed** - ✅ IMPLEMENTED
2. **Dark/Light Mode Toggle** - Improves UX immediately
3. **System Aggregated Statistics** - Enhances dashboard value

### Phase 2 (High Impact, Medium Complexity)
4. **Embeddable Status Badge** - Increases visibility
5. **Email Alerts** - ✅ IMPLEMENTED
6. **Data Export** - Enables external analysis

### Phase 3 (Medium Impact, Medium Complexity)
7. **Incident Timeline** - Transparency feature
8. **Scheduled Maintenance Windows** - Operational improvement

---

## Notes

- All features should respect the Raspberry Pi 1B+ constraints (low memory, CPU)
- Prefer stdlib solutions over external dependencies
- Maintain backward compatibility with existing API
- Follow existing code style and architecture patterns
- Add comprehensive tests for new features
- Update documentation (README.md) when features are implemented

---

## Excluded Features

The following features were considered but excluded due to lower priority or complexity:

- **JSON Feed**: Similar to RSS but less widely adopted
- **About Page**: Can be implemented manually if needed
- **Advanced History Filters**: Basic history endpoint is sufficient
- **Browser Push Notifications**: Complex, requires user permissions, HTTPS required
- **Social Media Sharing**: Nice-to-have but not critical
- **Metric Comparison**: Can be done externally with exported data
