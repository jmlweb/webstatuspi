# Task #040: RSS Feed Endpoint

## Metadata
- **Status**: done
- **Priority**: P1
- **Slice**: Backend, API
- **Created**: 2026-01-24
- **Started**: 2026-01-24
- **Completed**: 2026-01-24
- **Blocked by**: -

## Vertical Slice Definition

**User Story**: As a user, I want to subscribe to an RSS feed so that I get notified when service status changes without checking the dashboard.

**Acceptance Criteria**:
- [x] Endpoint `GET /rss.xml` returns valid RSS 2.0 XML
- [x] Include recent status changes (configurable max_items, default 20)
- [x] Each item has: title, description, pubDate, guid
- [x] Proper Content-Type header (`application/rss+xml`)
- [x] Configuration in `config.yaml` under `api.rss`
- [x] Endpoint disabled by default (enabled: false)

## Implementation Notes

### Add configuration to `config.py`

```python
class RssConfig:
    enabled: bool = False
    title: str = "WebStatusπ Status Feed"
    description: str = "Service status updates"
    max_items: int = 20
```

### Add endpoint to `api.py`

```python
@app.get("/rss.xml")
async def rss_feed():
    if not config.api.rss.enabled:
        raise HTTPException(404, "RSS feed disabled")

    # Get recent status changes from checks table
    # Generate RSS 2.0 XML using xml.etree.ElementTree

    return Response(content=xml_content, media_type="application/rss+xml")
```

### RSS 2.0 format

```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>WebStatusπ Status Feed</title>
    <link>https://status.example.com</link>
    <description>Service status updates</description>
    <lastBuildDate>Fri, 24 Jan 2026 12:00:00 GMT</lastBuildDate>
    <item>
      <title>APP_ES is DOWN</title>
      <description>Service returned status code 503</description>
      <pubDate>Fri, 24 Jan 2026 11:45:00 GMT</pubDate>
      <guid>APP_ES-2026-01-24T11:45:00</guid>
    </item>
  </channel>
</rss>
```

## Files to Modify

- `webstatuspi/config.py` - Add RssConfig class
- `webstatuspi/api.py` - Add /rss.xml endpoint
- `config.yaml` - Add example configuration

## Dependencies

None (stdlib `xml.etree.ElementTree`)

## Progress Log

- **2026-01-24**: Started (parallel execution with task #039)
- **2026-01-24**: Completed
  - Added `RssConfig` class to `config.py` with validation
  - Implemented RSS 2.0 XML generation with `_generate_rss_feed()` function
  - Added `/rss.xml` endpoint to `api.py` with proper error handling
  - Updated config.yaml with RSS configuration example
  - Added tests for RssConfig validation and config loading
  - All 406 tests passing
  - RSS feed returns recent status changes ordered by timestamp DESC
  - Proper RFC 822 date formatting for pubDate
  - Content-Type header set to `application/rss+xml`
  - Endpoint returns 404 when RSS is disabled
