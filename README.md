# WebStatusPi

Lightweight web monitoring system for Raspberry Pi 1B+. Monitors configured URLs, tracks success/failure statistics, and provides a JSON API for accessing monitoring data.

## Features

- ⚡ **Ultra-lightweight**: Designed for Raspberry Pi 1B+ (512MB RAM, single-core)
- 🔄 **Continuous monitoring**: Configurable global polling interval
- 📊 **Statistics tracking**: Success rate, failure count, response times
- 🌐 **JSON API**: Access monitoring data via HTTP
- 📝 **Console output**: Real-time display of check results
- 💾 **Persistent storage**: SQLite database for historical data

### Coming Soon

- 📟 **0.96" OLED display** for status visualization
  - Alert mode: Shows failing URLs with details
  - Normal mode: Rotates between status and statistics
  - Auto-rotation every 5 seconds
- 🔘 **Physical button** for screen navigation
  - Alert mode: Cycle through failed URLs
  - Normal mode: Switch between status/stats screens
  - Long press: Show overview of all URLs
- 🔊 **Buzzer alerts** on failures
  - Beeps for 30 seconds when URL transitions OK → FAIL
  - Silent when button pressed (acknowledge)
- 💡 **Status LEDs** (green=healthy, red=failure)
  - Green solid: All URLs OK
  - Red blinking: One or more URLs failing
  - Red solid: All URLs down

## Hardware Requirements

- Raspberry Pi 1B+ (or newer)
- MicroSD card (8GB+)
- Network connection (Ethernet)
- Optional (future): 0.96" I2C OLED display, button, buzzer, LEDs

## Software Requirements

- Raspberry Pi OS (Buster or newer)
- Python 3.7+

## Installation

### Option 1: Install from PyPI (when published)

```bash
pip install webstatuspi
```

### Option 2: Install from Source

**1. Clone Repository**

```bash
git clone <repository-url>
cd webstatuspi
```

**2. Install Package**

Using `pip`:
```bash
pip install .
```

Or with development dependencies:
```bash
pip install .[dev]
```

### 3. Configure Monitoring

Create a `config.yaml` file in the project root:

```yaml
monitor:
  interval: 60  # seconds between check cycles (default: 60)

urls:
  - name: "Google"
    url: "https://www.google.com"
    timeout: 10  # request timeout in seconds (default: 10)

  - name: "GitHub"
    url: "https://github.com"
    timeout: 10

api:
  enabled: true
  port: 8080
```

## Usage

### Start Monitoring

Using the installed command:
```bash
webstatuspi
```

Or using the Python module:
```bash
python3 -m webstatuspi
```

### Access API

**Get all stats:**
```bash
curl http://<pi-ip>:8080/
```

**Get specific URL stats:**
```bash
curl http://<pi-ip>:8080/status/Google
```

### Console Output Example

```
[2026-01-16 22:30:15] Google (https://www.google.com) - ✓ 200 OK (234ms)
[2026-01-16 22:30:18] GitHub (https://github.com) - ✓ 200 OK (456ms)
[2026-01-16 22:30:45] Google (https://www.google.com) - ✗ 503 Service Unavailable (123ms)
[2026-01-16 22:30:48] GitHub (https://github.com) - ✗ Connection timeout (10000ms)
```

- ✓ = Success (HTTP 2xx status code)
- ✗ = Failure (non-2xx status code or connection error)

## Project Structure

```
webstatuspi/
├── webstatuspi/          # Python package
│   ├── __init__.py       # Entry point (main function)
│   ├── __main__.py       # Module runner (python -m webstatuspi)
│   ├── api.py            # JSON API server
│   ├── config.py         # Configuration loader
│   ├── database.py       # Database operations
│   ├── models.py         # Data models (dataclasses)
│   └── monitor.py        # URL monitoring logic
├── tests/                # Unit tests
│   ├── test_api.py
│   ├── test_database.py
│   └── test_monitor.py
├── docs/
│   ├── ARCHITECTURE.md   # System architecture
│   ├── HARDWARE.md       # Hardware specifications
│   ├── dev/              # Development workflow
│   └── testing/          # Testing documentation
├── data/                 # Runtime data (auto-created)
│   └── monitoring.db     # SQLite database
├── config.yaml           # User configuration
├── pyproject.toml        # Python packaging
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Development dependencies
├── AGENTS.md             # Development rules
└── README.md             # This file
```

## API Reference

### GET /

Returns statistics for all monitored URLs.

**Response:**

```json
{
  "urls": [
    {
      "name": "Google",
      "url": "https://www.google.com",
      "total_requests": 150,
      "total_failures": 2,
      "success_rate": 98.67,
      "last_check": "2026-01-16T22:30:15",
      "last_status": "success",
      "last_status_code": 200
    },
    {
      "name": "GitHub",
      "url": "https://github.com",
      "total_requests": 150,
      "total_failures": 1,
      "success_rate": 99.33,
      "last_check": "2026-01-16T22:30:18",
      "last_status": "success",
      "last_status_code": 200
    }
  ],
  "summary": {
    "total_urls": 2,
    "total_requests": 300,
    "total_failures": 3,
    "overall_success_rate": 99.0
  }
}
```

### GET /status/{name}

Returns detailed statistics for a specific URL by name.

**Parameters:**
- `name`: URL name as configured in `config.yaml`

**Response:**

```json
{
  "name": "Google",
  "url": "https://www.google.com",
  "total_requests": 150,
  "total_failures": 2,
  "success_rate": 98.67,
  "last_check": "2026-01-16T22:30:15",
  "last_status": "success",
  "last_status_code": 200,
  "recent_checks": [
    {
      "timestamp": "2026-01-16T22:30:15",
      "status_code": 200,
      "response_time": 234,
      "success": true
    },
    {
      "timestamp": "2026-01-16T22:30:00",
      "status_code": 503,
      "response_time": 123,
      "success": false,
      "error_message": "Service Unavailable"
    }
  ]
}
```

**Errors:**
- `404 Not Found`: URL name doesn't exist in configuration

## OLED Display UI (Phase 2 - Coming Soon)

The 0.96" OLED display provides visual monitoring with Alert Mode and Normal Mode.

For detailed UI specifications, display state machine, GPIO pin assignments, and hardware configuration, see [Hardware Documentation](docs/HARDWARE.md).

## Configuration

### Server Settings

```yaml
server:
  port: 8080        # API server port
  host: 0.0.0.0     # Listen on all interfaces (use 127.0.0.1 for localhost only)
```

### Monitor Settings

```yaml
monitor:
  interval: 60  # Seconds between check cycles (default: 60, minimum: 1)
```

All URLs are checked together in each cycle. This simplifies configuration and ensures consistent timing across all monitored endpoints.

### URL Configuration

```yaml
urls:
  - name: "APP_ES"           # Required: unique identifier (max 10 chars)
    url: "https://example.com"  # Required: full URL with protocol
    timeout: 10              # Optional: request timeout in seconds (default: 10)
```

**Validation:**
- `name` must be unique across all URLs
- `name` must be ≤ 10 characters (optimized for OLED display)
- `name` should use uppercase and underscores (e.g., "APP_ES", "API_PROD")
- `url` must start with `http://` or `https://`
- `timeout` must be at least 1 second

### Database Configuration

```yaml
database:
  path: "./data/monitoring.db"  # Optional: database file path (default: "./data/monitoring.db")
  retention_days: 7              # Optional: days to keep check history (default: 7)
```

**Retention Notes:**
- Default retention of **7 days** balances useful history with SD card storage constraints
- With typical usage (5-10 URLs, 30-60s intervals): ~1.4 MB/day → 7 days ≈ **10 MB** total
- Older check records are automatically deleted (aggregated stats in `stats` table are preserved)
- Adjust `retention_days` based on your storage needs:
  - **7 days** (default): Recommended for most deployments (~10 MB)
  - **14 days**: For more history (~20 MB)
  - **30 days**: For extended history (~42 MB)

### Display & Hardware Configuration (Phase 2)

For detailed hardware configuration options, GPIO pin assignments, and hardware setup, see [Hardware Documentation](docs/HARDWARE.md).

## Performance Notes

The Raspberry Pi 1B+ has limited resources:

- **CPU**: Single-core 700MHz ARM11
- **RAM**: 512MB (shared with GPU, ~256MB available)
- **Network**: 10/100 Ethernet
- **Storage**: SD card (slow, wear considerations)

**Recommendations:**

- Monitor **5-10 URLs maximum** to avoid resource exhaustion
- Use intervals **≥30 seconds** to prevent CPU overload
- Set timeout **≤10 seconds** to avoid blocking
- Monitor system resources with `htop` during operation
- Avoid monitoring URLs with large response bodies

**Expected performance:**
- RAM usage: <200MB
- CPU usage: <20% with 5 URLs
- API response time: <100ms

## Troubleshooting

### High CPU Usage

**Symptoms**: Pi becomes sluggish, monitoring slows down

**Solutions:**
- Increase polling intervals in `config.yaml` (e.g., 60 seconds)
- Reduce number of monitored URLs
- Check for network timeouts (increase timeout value)
- Verify URLs aren't returning huge responses

### Database Growing Too Large

**Symptoms**: Slow queries, disk space issues

**Solutions:**

1. **Automatic cleanup** (recommended): The system automatically deletes checks older than `retention_days` (default: 7 days). This is configured in `config.yaml`:
   ```yaml
   database:
     retention_days: 7  # Adjust based on your needs
   ```

2. **Manual cleanup** (if automatic cleanup is not running):
   ```bash
   sqlite3 data/monitoring.db "DELETE FROM checks WHERE timestamp < datetime('now', '-7 days');"
   ```

3. **Check database size**:
   ```bash
   ls -lh data/monitoring.db
   ```

**Note**: Aggregated statistics in the `stats` table are preserved regardless of cleanup settings. Only individual `checks` records are deleted.

### API Not Accessible from Other Devices

**Symptoms**: Can't access `http://<pi-ip>:8080` from other devices

**Solutions:**

1. Check firewall (allow incoming connections on port 8080):
   ```bash
   sudo ufw allow 8080
   ```

2. Verify Pi IP address:
   ```bash
   ip addr show
   ```

3. Ensure server is listening on `0.0.0.0` (not `127.0.0.1`) in `config.yaml`

4. Check if port is already in use:
   ```bash
   netstat -tuln | grep 8080
   ```

### Monitoring Not Starting

**Symptoms**: Application exits immediately or shows errors

**Solutions:**

1. Verify `config.yaml` exists and is valid YAML
2. Check Python version (must be 3.7+):
   ```bash
   python3 --version
   ```
3. Ensure dependencies are installed:
   ```bash
   pip3 install -r requirements.txt
   ```
4. Check for permission issues with `data/` directory
5. Review error messages in console output

### Connection Timeouts

**Symptoms**: Many URLs showing "Connection timeout" errors

**Solutions:**

- Increase `timeout` value in `config.yaml` (e.g., 15 seconds)
- Check Pi's network connection: `ping google.com`
- Verify DNS is working: `nslookup google.com`
- Test URL manually: `curl -I <url>`

## Development

### Prerequisites

- Python 3.7+
- SQLite3

### Setup Development Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Database Schema

The application uses three SQLite tables:
1. **urls**: Stores monitored URL configurations
2. **checks**: Stores individual check results (detailed history)
3. **stats**: Stores aggregated statistics (fast queries)

For detailed schema information and database design rationale, see [Architecture Documentation](docs/ARCHITECTURE.md#database-design).

### Testing

Before deploying to Raspberry Pi:

1. Test with various URLs (success, failure, timeout scenarios)
2. Verify API endpoints return correct data
3. Monitor resource usage with `htop`
4. Test for extended periods (24+ hours) to check for memory leaks

**Testing without hardware:**

The project includes comprehensive mocking support for development without a Raspberry Pi. See [docs/testing/](docs/testing/) for:

- GPIO, I2C, and OLED display mocks ([MOCKING.md](docs/testing/MOCKING.md))
- Unit test examples with `pytest` and `unittest.mock` ([UNIT-TESTS.md](docs/testing/UNIT-TESTS.md))
- Automatic environment detection (Pi vs. development machine)
- Docker/QEMU emulation setup ([DOCKER-QEMU.md](docs/testing/DOCKER-QEMU.md))

```bash
# Run with mocks enabled
MOCK_GPIO=true MOCK_DISPLAY=true python3 main.py

# Run unit tests
python3 -m pytest tests/ -v

# Run with coverage
python3 -m pytest tests/ --cov=. --cov-report=html
```

See `AGENTS.md` for comprehensive testing checklist.

## Documentation

For detailed technical documentation:

- **[AGENTS.md](AGENTS.md)** - Development rules, code style, and conventions
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** - System architecture, design decisions, and data flow diagrams
- **[docs/HARDWARE.md](docs/HARDWARE.md)** - Hardware specifications, OLED display UI, and GPIO pin assignments
- **[docs/testing/](docs/testing/)** - Testing strategies and mocking guidelines for development without hardware

## Contributing

Contributions are welcome! Please read [AGENTS.md](AGENTS.md) for development guidelines and architecture decisions.

## License

[Specify your license here]

## Acknowledgments

Built for Raspberry Pi enthusiasts who want lightweight, reliable web monitoring without the overhead of heavy monitoring solutions.
