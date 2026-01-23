---
argument-hint: [branch]
description: Deploy to Raspberry Pi via git pull
model: haiku
---

# Deploy Skill

Deploy the application to a Raspberry Pi by pulling from git.

## Usage

- `/deploy` - Deploy current branch to Pi
- `/deploy main` - Deploy specific branch

## Prerequisites

- SSH key authentication configured (see `AGENTS.md`)
- `.env.local` file with: `PI_SSH_HOST`, `PI_SSH_USER`, `PI_SSH_PORT` (optional, default 22)
- Repository cloned on Pi at `/home/pi/webstatuspi`

## Workflow

### 1. Check Local State

```bash
git status --porcelain
git status -sb
```

If uncommitted changes, warn user and ask to commit first or continue.
If unpushed commits, ask to push first.

### 2. Deploy via SSH

**IMPORTANT**: Use direct SSH, not `./scripts/ssh-pi.sh` (the script doesn't work well with heredoc).

```bash
source .env.local
ssh -p ${PI_SSH_PORT:-22} ${PI_SSH_USER}@${PI_SSH_HOST} << 'EOF'
cd /home/pi/webstatuspi || exit 1
echo "Pulling changes..."
git fetch origin
git reset --hard origin/main
echo "Done. Latest commit:"
git log -1 --oneline
EOF
```

### 3. Restart Service

```bash
source .env.local
ssh -p ${PI_SSH_PORT:-22} ${PI_SSH_USER}@${PI_SSH_HOST} "sudo systemctl restart webstatuspi"
```

### 4. Verify Deployment

Wait 2-3 seconds for service to start, then verify:

```bash
curl -s http://webstatuspi.lan:8080/status | jq '.summary'
```

Expected output:
```json
{
  "total": 4,
  "up": 4,
  "down": 0
}
```

### 5. Report Status

```
Deployed to Pi

Branch: main
Commit: abc1234 feat: add new feature
Service: restarted
```

## Complete Deploy Command

For quick reference, here's the full deploy sequence:

```bash
# 1. Push changes
git push origin main

# 2. Deploy to Pi
source .env.local && ssh -p ${PI_SSH_PORT:-22} ${PI_SSH_USER}@${PI_SSH_HOST} << 'EOF'
cd /home/pi/webstatuspi || exit 1
git fetch origin
git reset --hard origin/main
EOF

# 3. Restart service
source .env.local && ssh -p ${PI_SSH_PORT:-22} ${PI_SSH_USER}@${PI_SSH_HOST} "sudo systemctl restart webstatuspi"

# 4. Verify (wait 2-3 seconds first)
sleep 3 && curl -s http://webstatuspi.lan:8080/status | jq '.summary'
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| SSH connection refused | Pi not reachable | Check network, verify `PI_SSH_HOST` |
| Permission denied | SSH key not configured | Run `ssh-copy-id` to Pi |
| Service restart failed | systemd not configured | Check `/etc/systemd/system/webstatuspi.service` |
| API not responding | Service crashed | Check logs: `journalctl -u webstatuspi -n 50` |

## Notes

- The Pi project path is `/home/pi/webstatuspi` (hardcoded, not configurable)
- Service name is `webstatuspi` (systemd unit)
- API runs on port 8080
- Use `webstatuspi.lan` or the Pi's IP address to access the dashboard
