# Task #004: API Server for JSON Stats

## Metadata
- **Status**: completed
- **Priority**: P1 - Active
- **Slice**: API
- **Created**: 2026-01-16
- **Started**: 2026-01-17
- **Completed**: 2026-01-17
- **Blocked by**: - (dependency #002 completed)

## Vertical Slice Definition

**User Story**: As a user/external system, I want to query current status via HTTP API.

**Acceptance Criteria**:
- [x] HTTP server running on configurable port
- [x] `GET /status` - Returns current status of all URLs
- [x] `GET /status/<name>` - Returns status of specific URL
- [x] `GET /health` - Returns API health check
- [x] JSON responses with proper Content-Type
- [x] Handle errors with appropriate HTTP codes
- [x] Runs in separate thread (non-blocking)

## Implementation Notes

### Using http.server (stdlib)
```python
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/status':
            data = get_all_status()
            self.send_json(200, data)
        elif self.path.startswith('/status/'):
            name = self.path[8:]  # after /status/
            data = get_status_by_name(name)
            if data:
                self.send_json(200, data)
            else:
                self.send_json(404, {"error": "URL not found"})
        elif self.path == '/health':
            self.send_json(200, {"status": "ok"})
        else:
            self.send_json(404, {"error": "Not found"})

    def send_json(self, code, data):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
```

### Response Format
```json
{
  "urls": [
    {
      "name": "Service A",
      "url": "https://example.com",
      "is_up": true,
      "status_code": 200,
      "response_time_ms": 150,
      "last_check": "2026-01-16T10:30:00Z"
    }
  ],
  "summary": {
    "total": 3,
    "up": 2,
    "down": 1
  }
}
```

### Pi 1B+ Constraints
- Single-threaded server is fine (low traffic expected)
- If using ThreadingMixIn, limit to 2 workers max
- Avoid keep-alive connections

## Files to Modify
- `webstatuspi/api.py` (create) - HTTP server implementation
- `webstatuspi/database.py` (update) - Add query methods if needed

## Dependencies
- #002 Database layer (for querying status)

## Progress Log
- [2026-01-17] Started task
- [2026-01-17] Created api.py with StatusHandler and ApiServer classes
- [2026-01-17] Implemented GET /status, /status/<name>, /health endpoints
- [2026-01-17] Added threading support with graceful shutdown
- [2026-01-17] Created 18 tests covering all endpoints and edge cases
- [2026-01-17] All 64 tests passing
- [2026-01-17] Task completed

## Learnings
(None yet)
