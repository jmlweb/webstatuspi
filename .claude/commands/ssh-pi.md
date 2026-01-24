---
argument-hint: <command>
description: Execute command on Raspberry Pi via SSH
model: haiku
---

# SSH to Raspberry Pi

Execute commands on the Raspberry Pi remotely.

## Usage

- `/ssh-pi "systemctl status webstatuspi"` - Check service status
- `/ssh-pi "journalctl -u webstatuspi -n 50"` - View recent logs
- `/ssh-pi "free -h && df -h"` - Check resources

## Connection Details

Environment variables in `.env.local`:

| Variable | Description |
|----------|-------------|
| `PI_SSH_HOST` | Hostname or IP (e.g., `webstatuspi.lan`) |
| `PI_SSH_USER` | SSH username (e.g., `claude`) |
| `PI_SSH_PORT` | SSH port (default: `22`) |

## Execute Command

```bash
source .env.local
ssh -p ${PI_SSH_PORT:-22} ${PI_SSH_USER}@${PI_SSH_HOST} "$ARGUMENTS"
```

If no command provided, show available options and ask what the user wants to do.

## Common Commands

| Task | Command |
|------|---------|
| Service status | `systemctl status webstatuspi` |
| Restart service | `sudo systemctl restart webstatuspi` |
| View logs (last 100) | `journalctl -u webstatuspi -n 100` |
| View errors only | `journalctl -u webstatuspi -p err -n 50` |
| Disk usage | `df -h` |
| Memory usage | `free -h` |
| CPU/processes | `top -bn1 | head -20` |
| Project git status | `cd /home/pi/webstatuspi && git log -1 --oneline` |

## Multi-line Commands

For commands with heredoc or multiple lines:

```bash
source .env.local
ssh -p ${PI_SSH_PORT:-22} ${PI_SSH_USER}@${PI_SSH_HOST} << 'EOF'
cd /home/pi/webstatuspi
git status
git log -3 --oneline
EOF
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Connection refused | Pi not reachable | Check network, verify hostname |
| Permission denied | SSH key not configured | See AGENTS.md for SSH key setup |
| Command not found | Wrong path or missing tool | Check command exists on Pi |

## Notes

- SSH key authentication required (no passwords)
- Project path on Pi: `/home/pi/webstatuspi`
- Service name: `webstatuspi` (systemd)
- API runs on port 8080
