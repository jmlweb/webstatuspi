# Troubleshooting Guide - WebStatusπ

Common issues and solutions when running WebStatusπ on Raspberry Pi.

## Rate Limiting (HTTP 429)

**Symptoms**: API returns `429 Too Many Requests` error.

**Diagnosis**:

```bash
# Check if you're hitting rate limits
curl -v http://localhost:8080/status
# Look for: HTTP/1.1 429 Too Many Requests
```

**Solutions**:

### 1. Wait and Retry

The rate limit is 60 requests per minute per IP. Wait ~1 minute before retrying.

### 2. Use a Different IP

Rate limiting is per-IP. Local/private IPs (127.0.0.1, 192.168.x.x) are exempt.

### 3. Reduce Polling Frequency

If using automated tools, increase the interval between requests:

```bash
# Instead of every second, poll every 10 seconds
watch -n 10 'curl -s http://localhost:8080/status | jq .summary'
```

---

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
# Check database size (default XDG location)
ls -lh ~/.local/share/webstatuspi/status.db

# Or if using custom path from config
ls -lh /path/to/your/status.db

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
# Delete checks older than 7 days (using default XDG path)
sqlite3 ~/.local/share/webstatuspi/status.db "DELETE FROM checks WHERE checked_at < datetime('now', '-7 days');"

# Reclaim disk space after deletion
sqlite3 ~/.local/share/webstatuspi/status.db "VACUUM;"
```

### 3. Check What's Using Space

```bash
# Count total records
sqlite3 ~/.local/share/webstatuspi/status.db "SELECT COUNT(*) as total_checks FROM checks;"

# Check records by URL
sqlite3 ~/.local/share/webstatuspi/status.db "SELECT url_name, COUNT(*) as checks FROM checks GROUP BY url_name;"

# Check oldest record
sqlite3 ~/.local/share/webstatuspi/status.db "SELECT MIN(checked_at) FROM checks;"
```

### 4. Use API Reset Endpoint

For a complete reset (deletes ALL data):

```bash
# If no token configured
curl -X DELETE http://localhost:8080/reset

# If token is configured
curl -X DELETE http://localhost:8080/reset -H "Authorization: Bearer your-token"
```

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

## PWA Install Option Missing on Android

**Symptoms**: Chrome on Android does not show "Install app" or "Add to Home Screen."

**Diagnosis**:

1. **Check for HTTPS**:
   - PWA install requires a secure context.
   - If the URL starts with `http://` (not `https://`) on a phone or tablet, install is disabled.

2. **Check Service Worker Registration**:
   - In Chrome, open `chrome://inspect` and attach to the device.
   - Look for console errors like `Only secure origins are allowed`.

**Solutions**:

### 1. Serve the Dashboard over HTTPS (Recommended)

Use one of these options:

- Reverse proxy (nginx) with Let's Encrypt
- Cloudflare Tunnel (if the Pi is reachable by domain)

### 2. Development-Only Workarounds

- Use `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
- Add `http://<pi-ip>:8080` to the allowed list
- Reload the page

### 3. Reload After First Visit

The install prompt can appear only after the Service Worker controls the page.
Reload once after the first visit and check the menu again.

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

**Symptoms**: WebStatusπ doesn't start automatically after reboot.

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
Description=WebStatusπ URL Monitor
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

## Reset Endpoint Not Working

**Symptoms**: `DELETE /reset` returns 403 or 401 error.

**Solutions**:

### 1. Error: "Nice try, Diddy! You are not allowed to perform this action" (403)

This means you're accessing the endpoint through Cloudflare. The reset endpoint is blocked for external access as a security measure.

**Fix**: Access directly from the local network or the Pi itself:

```bash
# From the Raspberry Pi
curl -X DELETE http://localhost:8080/reset

# From local network (not through Cloudflare)
curl -X DELETE http://192.168.1.50:8080/reset
```

### 2. Error: "Authorization required: Bearer token expected" (401)

Your configuration has `api.reset_token` set, requiring authentication.

**Fix**: Include the Authorization header:

```bash
curl -X DELETE http://localhost:8080/reset \
  -H "Authorization: Bearer your-configured-token"
```

### 3. Error: "Invalid reset token" (403)

The token you provided doesn't match the configured token.

**Fix**: Check your `config.yaml` for the correct token:

```yaml
api:
  port: 8080
  reset_token: "your-secret-token"  # Use this exact value
```

Or check the environment variable:

```bash
echo $WEBSTATUS_API_RESET_TOKEN
```

---

## Telegram Notifications Not Working

**Symptoms**: Telegram alerts not arriving despite webhook being configured.

**Solutions**:

### 1. Verify Bot Token

```bash
# Test if your bot token is valid
curl "https://api.telegram.org/botYOUR_TOKEN/getMe"
```

Expected: JSON with your bot info. If you get `{"ok":false}`, the token is invalid.

### 2. Verify Chat ID

```bash
# Send a test message directly
curl -X POST "https://api.telegram.org/botYOUR_TOKEN/sendMessage" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": "YOUR_CHAT_ID", "text": "Test"}'
```

Common chat ID issues:
- Personal IDs are positive numbers (e.g., `123456789`)
- Group IDs are negative (e.g., `-123456789`)
- Supergroups start with `-100` (e.g., `-1001234567890`)

### 3. Check Relay Service

WebStatusπ sends generic webhooks that need transformation for Telegram. Verify your relay service (Pipedream, n8n, etc.) is:
- Running and receiving webhooks
- Properly configured with your bot token and chat ID
- Not hitting rate limits

```bash
# Test WebStatusπ webhook delivery
webstatuspi test-alert --verbose
```

### 4. Bot Not in Group

If using group notifications:
1. Ensure the bot is still in the group
2. The bot must have permission to send messages
3. Re-add the bot and get new chat ID if needed

For detailed setup instructions, see [Telegram Setup Guide](TELEGRAM_SETUP.md).

## Getting Help

If none of these solutions work:

1. Check the [GitHub Issues](https://github.com/jmlweb/webstatuspi/issues)
2. Run with `--verbose` flag and share the output
3. Include your `config.yaml` (remove sensitive URLs) when reporting issues

## Related Documentation

- [Architecture](ARCHITECTURE.md) - System design and error handling strategies
- [Hardware](HARDWARE.md) - Hardware-specific troubleshooting
- [Telegram Setup](TELEGRAM_SETUP.md) - Telegram bot configuration guide
- [Testing](testing/) - Development and debugging tools
