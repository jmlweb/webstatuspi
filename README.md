# WebStatusPi

Ultra-lightweight web monitoring system designed for **Raspberry Pi 1B+**. Monitor your websites, track uptime statistics, and access data via a simple JSON API.

## Quick Start

### Requirements

- Raspberry Pi 1B+ (or newer) with Raspberry Pi OS
- Python 3.7+
- Network connection

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/jmlweb/webstatuspi.git
cd webstatuspi

# 2. Install the package
pip install .

# 3. Create your configuration file
cp config.example.yaml config.yaml
```

### Configuration

Edit `config.yaml` with your URLs:

```yaml
monitor:
  interval: 60  # seconds between checks

urls:
  - name: "UB_APP"
    url: "https://app.unobravo.com"
    timeout: 5

  - name: "UB_WEB"
    url: "https://www.unobravo.com"
    timeout: 5

api:
  enabled: true
  port: 8080
```

### Run

```bash
webstatuspi
```

That's it! The monitor will start checking your URLs and the API will be available at `http://<your-pi-ip>:8080`.

### Auto-start on Boot (Optional)

WebStatusPi can install itself as a systemd service automatically:

```bash
# Preview the service file (no changes made)
webstatuspi install-service --dry-run

# Install, enable, and start the service
sudo webstatuspi install-service --enable --start
```

**Options:**

| Option | Description |
|--------|-------------|
| `--user USER` | User to run the service as (default: current user) |
| `--working-dir DIR` | Working directory (default: current directory) |
| `--enable` | Enable auto-start on boot |
| `--start` | Start the service immediately |
| `--dry-run` | Preview without installing |

**Useful commands:**

```bash
sudo systemctl status webstatuspi   # Check status
sudo journalctl -u webstatuspi -f   # View logs
sudo systemctl restart webstatuspi  # Restart service
```

<details>
<summary>Manual installation (alternative)</summary>

Create `/etc/systemd/system/webstatuspi.service`:

```ini
[Unit]
Description=WebStatusPi URL Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/webstatuspi
ExecStart=/usr/bin/python3 -m webstatuspi run
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then enable: `sudo systemctl daemon-reload && sudo systemctl enable --now webstatuspi`

</details>

---

## Features

- **Ultra-lightweight**: Runs smoothly on Raspberry Pi 1B+ (512MB RAM, single-core)
- **Continuous monitoring**: Configurable polling intervals
- **Statistics tracking**: Success rate, failure count, response times
- **JSON API**: Access monitoring data via HTTP
- **Console output**: Real-time display of check results
- **Persistent storage**: SQLite database for historical data

### Coming Soon

- 0.96" OLED display for status visualization
- Physical button for screen navigation
- Buzzer alerts on failures
- Status LEDs (green/red)

---

## Usage

### Console Output

When running, you'll see real-time results:

```
[2026-01-16 22:30:15] UB_APP (https://app.unobravo.com) - ✓ 200 OK (234ms)
[2026-01-16 22:30:18] UB_WEB (https://www.unobravo.com) - ✓ 200 OK (456ms)
[2026-01-16 22:30:45] UB_APP (https://app.unobravo.com) - ✗ 503 Service Unavailable (123ms)
```

### API Endpoints

**Get all stats:**

```bash
curl http://<pi-ip>:8080/status
```

**Get specific URL stats:**

```bash
curl http://<pi-ip>:8080/status/UB_APP
```

**Health check:**

```bash
curl http://<pi-ip>:8080/health
```

<details>
<summary>Example API Response</summary>

```json
{
  "urls": [
    {
      "name": "UB_APP",
      "url": "https://app.unobravo.com",
      "total_requests": 150,
      "total_failures": 2,
      "success_rate": 98.67,
      "last_check": "2026-01-16T22:30:15",
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

</details>

---

## Configuration Reference

### Monitor Settings

```yaml
monitor:
  interval: 60  # seconds between check cycles (default: 60, min: 1)
```

### URL Configuration

```yaml
urls:
  - name: "APP_ES"              # unique identifier (max 10 chars)
    url: "https://example.com"  # full URL with protocol
    timeout: 10                 # request timeout in seconds (default: 10)
```

### Server Settings

```yaml
server:
  port: 8080      # API server port
  host: 0.0.0.0   # listen on all interfaces
```

### Database Settings

```yaml
database:
  path: "./data/monitoring.db"  # database file path
  retention_days: 7             # days to keep check history
```

---

## Troubleshooting

<details>
<summary>API not accessible from other devices</summary>

1. Check firewall: `sudo ufw allow 8080`
2. Verify Pi IP: `ip addr show`
3. Ensure server listens on `0.0.0.0` in config

</details>

<details>
<summary>High CPU usage</summary>

- Increase polling interval (e.g., 60+ seconds)
- Reduce number of monitored URLs
- Check for network timeouts

</details>

<details>
<summary>Connection timeouts</summary>

- Increase `timeout` value in config
- Check network: `ping google.com`
- Test URL manually: `curl -I <url>`

</details>

<details>
<summary>Monitoring not starting</summary>

1. Verify `config.yaml` exists and is valid
2. Check Python version: `python3 --version` (must be 3.7+)
3. Ensure dependencies installed: `pip install -r requirements.txt`

</details>

For detailed troubleshooting with commands and examples, see [Troubleshooting Guide](docs/TROUBLESHOOTING.md).

---

## Performance Notes

Optimized for Raspberry Pi 1B+ constraints:

| Metric | Target |
|--------|--------|
| RAM usage | < 200MB |
| CPU usage | < 20% (with 5 URLs) |
| API response | < 100ms |

**Recommendations:**
- Monitor 5-10 URLs maximum
- Use intervals of 30+ seconds
- Set timeout to 10 seconds or less

---

## Development

### Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install with dev dependencies
pip install .[dev]

# Run tests
python3 -m pytest tests/ -v
```

### Project Structure

```
webstatuspi/
├── webstatuspi/          # Python package
│   ├── __init__.py       # Entry point and CLI
│   ├── api.py            # JSON API server
│   ├── config.py         # Configuration loader
│   ├── database.py       # Database operations
│   ├── monitor.py        # URL monitoring logic
│   └── service.py        # Systemd service installer
├── tests/                # Unit tests
├── docs/                 # Documentation
│   ├── ARCHITECTURE.md   # System architecture
│   ├── HARDWARE.md       # Hardware specs
│   └── testing/          # Testing guides
└── config.yaml           # Your configuration
```

---

## Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design and database schema
- [Hardware](docs/HARDWARE.md) - GPIO pins, OLED display setup
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Detailed problem solving guide
- [Testing](docs/testing/) - Mocking guides for development without hardware
- [Development Rules](AGENTS.md) - Code style and conventions

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

---

Built for Raspberry Pi enthusiasts who want lightweight, reliable web monitoring.
