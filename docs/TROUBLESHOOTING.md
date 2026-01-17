# Troubleshooting Guide - WebStatusPi

Common issues and solutions when running WebStatusPi on Raspberry Pi.

## High CPU Usage

**Symptoms**: Pi becomes sluggish, monitoring slows down, high temperature.

**Diagnosis**:

```bash
# Check CPU usage
htop

# Check webstatuspi process specifically
ps aux | grep webstatuspi
```

**Solutions**:

1. **Increase polling interval** in `config.yaml`:
   ```yaml
   monitor:
     interval: 60  # Increase to 60+ seconds
   ```

2. **Reduce number of monitored URLs** - Keep to 5-10 maximum

3. **Check for network timeouts** - Increase timeout to reduce retry overhead:
   ```yaml
   urls:
     - name: "SlowSite"
       url: "https://slow-site.com"
       timeout: 15  # Increase from default 10
   ```

4. **Verify URLs aren't returning huge responses** - Large response bodies consume more CPU

## Database Growing Too Large

**Symptoms**: Slow API queries, disk space warnings, SD card filling up.

**Diagnosis**:

```bash
# Check database size
ls -lh data/monitoring.db

# Check disk usage
df -h
```

**Solutions**:

### 1. Automatic Cleanup (Recommended)

The system automatically deletes checks older than `retention_days`. Configure in `config.yaml`:

```yaml
database:
  retention_days: 7  # Adjust based on your needs
```

**Retention guidelines**:
- **7 days** (default): ~10 MB, recommended for most deployments
- **14 days**: ~20 MB, for more history
- **30 days**: ~42 MB, for extended history

### 2. Manual Cleanup

If automatic cleanup is not running or you need immediate space:

```bash
# Delete checks older than 7 days
sqlite3 data/monitoring.db "DELETE FROM checks WHERE timestamp < datetime('now', '-7 days');"

# Reclaim disk space after deletion
sqlite3 data/monitoring.db "VACUUM;"
```

### 3. Check What's Using Space

```bash
# Count records per table
sqlite3 data/monitoring.db "SELECT 'checks', COUNT(*) FROM checks UNION SELECT 'stats', COUNT(*) FROM stats UNION SELECT 'urls', COUNT(*) FROM urls;"

# Check oldest record
sqlite3 data/monitoring.db "SELECT MIN(timestamp) FROM checks;"
```

**Note**: Aggregated statistics in the `stats` table are preserved regardless of cleanup. Only individual `checks` records are deleted.

## API Not Accessible from Other Devices

**Symptoms**: Can access `http://localhost:8080` on Pi but not `http://<pi-ip>:8080` from other devices.

**Diagnosis**:

```bash
# Check if server is running and on which interface
netstat -tuln | grep 8080

# Expected output for accessible server:
# tcp  0  0  0.0.0.0:8080  0.0.0.0:*  LISTEN
# If you see 127.0.0.1:8080, it's only accessible locally
```

**Solutions**:

### 1. Verify Server Configuration

Ensure `config.yaml` has the server listening on all interfaces:

```yaml
server:
  host: 0.0.0.0  # NOT 127.0.0.1
  port: 8080
```

### 2. Check Firewall

```bash
# Check if ufw is active
sudo ufw status

# Allow port 8080
sudo ufw allow 8080

# Or allow from specific network only
sudo ufw allow from 192.168.1.0/24 to any port 8080
```

### 3. Verify Pi IP Address

```bash
# Get Pi's IP address
ip addr show | grep "inet "

# Or use hostname
hostname -I
```

### 4. Test Connectivity

From another device:

```bash
# Test if port is reachable
nc -zv <pi-ip> 8080

# Test API endpoint
curl -v http://<pi-ip>:8080/
```

### 5. Check if Port is Already in Use

```bash
# See what's using port 8080
sudo lsof -i :8080

# Kill conflicting process if needed
sudo kill <PID>
```

## Monitoring Not Starting

**Symptoms**: Application exits immediately, shows errors on startup, or hangs.

**Diagnosis**:

```bash
# Run with verbose output
webstatuspi --verbose

# Or run as module for more debug info
python3 -m webstatuspi
```

**Solutions**:

### 1. Verify Configuration File

```bash
# Check if config.yaml exists
ls -la config.yaml

# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

Common YAML errors:
- Missing colons after keys
- Incorrect indentation (use spaces, not tabs)
- Unquoted special characters

### 2. Check Python Version

```bash
python3 --version
# Must be 3.7 or higher
```

### 3. Verify Dependencies

```bash
# Reinstall dependencies
pip install -r requirements.txt

# Or reinstall package
pip install --force-reinstall .
```

### 4. Check Data Directory Permissions

```bash
# Create data directory if missing
mkdir -p data

# Check permissions
ls -la data/

# Fix permissions if needed
chmod 755 data/
```

### 5. Check for Import Errors

```bash
# Test imports
python3 -c "from webstatuspi import main; print('OK')"
```

## Connection Timeouts

**Symptoms**: Many URLs showing "Connection timeout" errors, checks taking too long.

**Diagnosis**:

```bash
# Test network connectivity
ping -c 4 google.com

# Test DNS resolution
nslookup google.com

# Test specific URL manually
curl -I -m 10 https://example.com
```

**Solutions**:

### 1. Increase Timeout Value

```yaml
urls:
  - name: "SlowSite"
    url: "https://slow-responding-site.com"
    timeout: 15  # Increase from default 10
```

### 2. Check Network Configuration

```bash
# Check network interface status
ip link show

# Check DNS servers
cat /etc/resolv.conf

# Test with specific DNS
nslookup google.com 8.8.8.8
```

### 3. Check for Network Issues

```bash
# Check route to internet
traceroute google.com

# Check if Ethernet cable is connected (Pi 1B+)
ethtool eth0 | grep "Link detected"
```

### 4. Verify URLs are Correct

```bash
# Test each URL manually
curl -I https://your-url.com
```

## Memory Issues

**Symptoms**: Pi becomes unresponsive, processes killed by OOM killer, swap usage high.

**Diagnosis**:

```bash
# Check memory usage
free -h

# Check for OOM killer messages
dmesg | grep -i "out of memory"

# Monitor memory over time
watch -n 5 free -h
```

**Solutions**:

### 1. Reduce Number of URLs

Keep to 5-10 URLs maximum for Pi 1B+.

### 2. Increase Swap (Temporary Fix)

```bash
# Check current swap
swapon --show

# Increase swap size (not recommended long-term on SD card)
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile  # Set CONF_SWAPSIZE=512
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

### 3. Reduce GPU Memory

Edit `/boot/config.txt`:

```
gpu_mem=16
```

This frees up ~240MB for the system.

### 4. Check for Memory Leaks

Run for extended period and monitor:

```bash
# Log memory usage every minute
while true; do date >> /tmp/memlog.txt; free -h >> /tmp/memlog.txt; sleep 60; done
```

## SD Card Wear Concerns

**Symptoms**: Worried about SD card lifespan, frequent writes.

**Best Practices**:

### 1. Use Appropriate Retention

```yaml
database:
  retention_days: 7  # Shorter retention = fewer writes
```

### 2. Use Quality SD Card

- Use Class 10 or UHS-I cards
- Prefer cards designed for continuous write (industrial/endurance cards)

### 3. Monitor SD Card Health

```bash
# Check for filesystem errors
sudo fsck -n /dev/mmcblk0p2

# Check SMART data (if supported)
sudo smartctl -a /dev/mmcblk0
```

### 4. Consider USB Storage

For long-term deployments, use USB drive instead of SD card for database:

```yaml
database:
  path: "/mnt/usb/monitoring.db"
```

## Service Won't Start on Boot

**Symptoms**: WebStatusPi doesn't start automatically after reboot.

**Solutions**:

### 1. Install the Service Automatically

Use the built-in installer:

```bash
# Preview the service file first
webstatuspi install-service --dry-run

# Install, enable, and start
sudo webstatuspi install-service --enable --start
```

### 2. Verify Installation

```bash
# Check status
sudo systemctl status webstatuspi

# View logs
journalctl -u webstatuspi -f
```

### 3. Manual Installation (Alternative)

If automatic installation fails, create `/etc/systemd/system/webstatuspi.service` manually:

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

Then enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now webstatuspi
```

## Getting Help

If none of these solutions work:

1. Check the [GitHub Issues](https://github.com/jmlweb/webstatuspi/issues)
2. Run with `--verbose` flag and share the output
3. Include your `config.yaml` (remove sensitive URLs) when reporting issues

## Related Documentation

- [Architecture](ARCHITECTURE.md) - System design and error handling strategies
- [Hardware](HARDWARE.md) - Hardware-specific troubleshooting
- [Testing](testing/) - Development and debugging tools
