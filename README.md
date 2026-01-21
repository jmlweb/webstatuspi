<p align="center">
  <img src="https://img.shields.io/badge/platform-Raspberry%20Pi-C51A4A?style=for-the-badge&logo=raspberry-pi" alt="Raspberry Pi">
  <img src="https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="MIT License">
</p>

<p align="center">
  <a href="https://github.com/jmlweb/webstatuspi/actions/workflows/test.yml"><img src="https://github.com/jmlweb/webstatuspi/actions/workflows/test.yml/badge.svg" alt="Test"></a>
  <a href="https://github.com/jmlweb/webstatuspi/actions/workflows/lint.yml"><img src="https://github.com/jmlweb/webstatuspi/actions/workflows/lint.yml/badge.svg" alt="Lint"></a>
</p>

<h1 align="center">🖥️ WebStatusPi</h1>

<p align="center">
  <strong>Ultra-lightweight web monitoring for Raspberry Pi</strong><br>
  <em>Track uptime, response times, and get instant alerts — all from a $35 computer</em>
</p>

<p align="center">
  <img src="dashboard-home.png" alt="Dashboard Preview" width="600">
</p>

---

## ✨ Why WebStatusPi?

| Feature | Benefit |
|---------|---------|
| **🪶 Ultra-lightweight** | Runs on Raspberry Pi 1B+ (512MB RAM) |
| **📊 Real-time Dashboard** | CRT-style cyberpunk interface |
| **🔌 JSON API** | Integrate with anything |
| **💾 Persistent Storage** | SQLite keeps your history safe |
| **⚡ Zero Config** | Works out of the box |

### Resource Comparison

How does WebStatusPi compare to popular alternatives?

**Runtime Performance** (Docker benchmark: 5 URLs, 60s interval, 10 samples)

| Tool | RAM Usage | CPU Usage | Docker Image |
|------|-----------|-----------|--------------|
| **WebStatusPi** | **17 MB** | 0.2% | 61 MB |
| Statping-ng | 30 MB | 0.5% | 58 MB |
| Uptime Kuma | 114 MB | 0.2% | 439 MB |

**Installation Size on Raspberry Pi** (native, no Docker)

| Tool | Install Size | Requires |
|------|--------------|----------|
| **WebStatusPi** | **~1 MB** | Nothing (uses system Python) |
| Statping-ng | ~58 MB | Go binary |
| Uptime Kuma | ~150 MB | Node.js runtime |

*WebStatusPi leverages the Python already installed on Raspberry Pi OS. Run `./benchmark/benchmark.sh` to reproduce the runtime benchmark.*

---

## 🚀 Quick Start

### One-Line Install (Recommended)

Run this on your Raspberry Pi:

```bash
curl -sSL https://raw.githubusercontent.com/jmlweb/webstatuspi/main/install.sh | bash
```

The interactive installer will:
- Install dependencies and create a virtual environment
- Guide you through URL configuration
- Optionally set up auto-start on boot

**That's it!** Open `http://<your-pi-ip>:8080` in your browser.

<details>
<summary>📦 Manual Installation</summary>

```bash
# Clone and install
git clone https://github.com/jmlweb/webstatuspi.git
cd webstatuspi
python3 -m venv venv
source venv/bin/activate
pip install .

# Configure
cp config.example.yaml config.yaml
# Edit config.yaml with your URLs

# Run
webstatuspi
```

</details>

<details>
<summary>⚙️ Installer Options</summary>

```bash
# Interactive installation
./install.sh

# Non-interactive with defaults
./install.sh --non-interactive

# System-wide installation (with systemd service)
sudo ./install.sh --install-dir /opt/webstatuspi

# Update existing installation
./install.sh --update

# Uninstall
./install.sh --uninstall
```

</details>

---

## 📺 Dashboard

<table>
<tr>
<td width="50%">

### Overview
<img src="dashboard-home.png" alt="Dashboard Home" width="100%">

Real-time status cards with latency and 24h uptime metrics.

</td>
<td width="50%">

### Detail View
<img src="dashboard-detail.png" alt="Dashboard Detail" width="100%">

Click any card to see full check history with timestamps.

</td>
</tr>
</table>

**Features:**
- 🔄 Auto-refresh every 10 seconds
- 🟢🔴 Color-coded status indicators
- 📈 Response time graphs
- 🕹️ Retro CRT aesthetic with scanlines

---

## 🔧 API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Web dashboard |
| `GET` | `/status` | All URLs status |
| `GET` | `/status/{name}` | Specific URL status |
| `GET` | `/health` | Health check |

### Example Response

```bash
curl http://localhost:8080/status
```

```json
{
  "urls": [
    {
      "name": "MY_SITE",
      "url": "https://example.com",
      "success_rate": 99.5,
      "last_status": "success",
      "last_status_code": 200
    }
  ],
  "summary": {
    "total_urls": 1,
    "overall_success_rate": 99.5
  }
}
```

---

## 🔄 Auto-Start on Boot

Install as a systemd service:

```bash
# Preview what will be installed
webstatuspi install-service --dry-run

# Install and start
sudo webstatuspi install-service --enable --start
```

<details>
<summary>📋 Service management commands</summary>

```bash
sudo systemctl status webstatuspi   # Check status
sudo journalctl -u webstatuspi -f   # View live logs
sudo systemctl restart webstatuspi  # Restart
sudo systemctl stop webstatuspi     # Stop
```

</details>

---

## ⚙️ Configuration

### Full Example

```yaml
monitor:
  interval: 60              # seconds between checks

urls:
  - name: "PROD_API"        # max 10 characters
    url: "https://api.example.com"
    timeout: 10

  - name: "STAGING"
    url: "https://staging.example.com"
    timeout: 5

server:
  port: 8080
  host: 0.0.0.0             # listen on all interfaces

database:
  path: "./data/monitoring.db"
  retention_days: 7         # auto-cleanup old data
```

### Performance Tips

For Raspberry Pi 1B+:

| Setting | Recommendation |
|---------|----------------|
| URLs | 5-10 max |
| Interval | 30+ seconds |
| Timeout | 10s or less |

---

## 🛠️ Development

```bash
# Setup
python3 -m venv venv
source venv/bin/activate
pip install .[dev]

# Run tests
pytest tests/ -v

# Run benchmark (Docker required)
cd benchmark && ./benchmark.sh
```

### Project Structure

```
webstatuspi/
├── webstatuspi/        # Core package
│   ├── __init__.py     # CLI entry point
│   ├── api.py          # HTTP server
│   ├── database.py     # SQLite operations
│   └── monitor.py      # URL checker
├── tests/              # Test suite
└── docs/               # Documentation
```

---

## 🔮 Roadmap

- [ ] 0.96" OLED display support
- [ ] Physical button navigation
- [ ] Buzzer alerts on failures
- [ ] Status LEDs (green/red)

---

## 🐛 Troubleshooting

<details>
<summary><strong>API not accessible from other devices</strong></summary>

1. Check firewall: `sudo ufw allow 8080`
2. Verify config has `host: 0.0.0.0`
3. Check Pi IP: `ip addr show`

</details>

<details>
<summary><strong>High CPU usage</strong></summary>

- Increase polling interval to 60+ seconds
- Reduce number of monitored URLs
- Check for slow/timing out URLs

</details>

<details>
<summary><strong>Connection timeouts</strong></summary>

- Increase `timeout` value in config
- Test network: `ping google.com`
- Test URL manually: `curl -I <url>`

</details>

See [Troubleshooting Guide](docs/TROUBLESHOOTING.md) for more.

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System design & database schema |
| [Hardware](docs/HARDWARE.md) | GPIO pins & OLED setup |
| [Contributing](CONTRIBUTING.md) | How to contribute |
| [Development Rules](AGENTS.md) | Code style & conventions |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  <strong>Built with ❤️ for Raspberry Pi enthusiasts</strong><br>
  <em>Lightweight. Reliable. Open Source.</em>
</p>
