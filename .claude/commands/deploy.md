---
argument-hint: [pi-host]
description: Deploy to Raspberry Pi via SSH
model: haiku
---

# Deploy Skill

Deploy the application to a Raspberry Pi over SSH.

## Usage

- `/deploy` - Deploy to Pi configured in `.env.local`
- `/deploy user@192.168.1.100` - Deploy to specific host (override)

## Prerequisites

- SSH key authentication configured
- Pi accessible on network
- Target directory exists on Pi
- `.env.local` file configured (see below)

## Configuration

Create `.env.local` from the template:

```bash
cp .env.local.example .env.local
# Edit .env.local with your values
```

Environment variables used:

| Variable | Description | Default |
|----------|-------------|---------|
| `PI_SSH_HOST` | Hostname or IP | (required) |
| `PI_SSH_USER` | SSH username | (required) |
| `PI_SSH_PORT` | SSH port | `22` |
| `PI_PROJECT_PATH` | Install path on Pi | `/opt/webstatuspi` |
| `PI_SERVICE_NAME` | systemd service name | `webstatuspi` |

## Workflow

### 1. Load Configuration

```bash
# Load environment variables
source .env.local

# Validate required variables are set
if [[ -z "$PI_SSH_HOST" || -z "$PI_SSH_USER" ]]; then
    echo "Error: PI_SSH_HOST and PI_SSH_USER must be set in .env.local"
    exit 1
fi

# Set defaults
PI_SSH_PORT="${PI_SSH_PORT:-22}"
PI_PROJECT_PATH="${PI_PROJECT_PATH:-/opt/webstatuspi}"
PI_SERVICE_NAME="${PI_SERVICE_NAME:-webstatuspi}"

# Build SSH target
SSH_TARGET="$PI_SSH_USER@$PI_SSH_HOST"
SSH_OPTS="-p $PI_SSH_PORT"
```

If argument provided, override:
```bash
# /deploy claude@192.168.1.50 overrides .env.local
SSH_TARGET="$1"
```

### 2. Validate Local State

```bash
# Check for uncommitted changes
git status --porcelain
```

If uncommitted changes:
```
⚠️ Uncommitted changes detected

Files:
- src/monitor.py (modified)
- config.yaml (modified)

Options:
1. Deploy anyway (changes included)
2. Commit first (/commit)
3. Abort deployment
```

### 3. Run Pre-deploy Checks

```bash
# Syntax check all Python files
python3 -m py_compile src/*.py

# Run tests if they exist
pytest tests/ -q --tb=no 2>/dev/null || echo "No tests or tests failed"
```

If syntax errors:
```
❌ Syntax errors found - aborting deployment

Fix errors before deploying:
- src/monitor.py: line 45 - invalid syntax
```

### 4. Create Deployment Package

```bash
# Files to deploy (uses variables from .env.local)
rsync -avz $SSH_OPTS --exclude='.git' \
           --exclude='__pycache__' \
           --exclude='*.pyc' \
           --exclude='.claude' \
           --exclude='.env.local' \
           --exclude='venv' \
           --exclude='data/*.db' \
           ./ "$SSH_TARGET:$PI_PROJECT_PATH/"
```

### 5. Remote Setup (if first deploy)

```bash
./scripts/ssh-pi.sh << 'EOF'
  cd "$PI_PROJECT_PATH"

  # Create venv if not exists
  [ ! -d venv ] && python3 -m venv venv

  # Install dependencies
  venv/bin/pip install -r requirements.txt

  # Create data directory
  mkdir -p data

  # Set permissions
  chmod +x src/main.py
EOF
```

### 6. Restart Service

```bash
./scripts/ssh-pi.sh "sudo systemctl restart $PI_SERVICE_NAME 2>/dev/null || echo 'Service not installed'"
```

### 7. Verify Deployment

```bash
# Check if running
./scripts/ssh-pi.sh "curl -s http://localhost:8080/api/health 2>/dev/null || echo 'API not responding'"
```

### 8. Report Status

```
✓ Deployed to $SSH_TARGET

Files synced: 15
Service: restarted
API health: OK

Deployment log: $PI_PROJECT_PATH/deploy.log
```

## Rollback

If deployment fails:
```
❌ Deployment failed

Last working version backed up at:
$PI_PROJECT_PATH.backup/

To rollback manually:
./scripts/ssh-pi.sh "sudo mv $PI_PROJECT_PATH.backup $PI_PROJECT_PATH && sudo systemctl restart $PI_SERVICE_NAME"
```

## Error Handling

- SSH connection failed: Check network and `.env.local` configuration
- Rsync failed: Check disk space on Pi
- Service restart failed: Check systemd logs
- API not responding: Check application logs

## Security Notes

- **Never hardcode hosts/users** - always use `.env.local` variables
- **`.env.local` is gitignored** - safe to store real values
- Use `./scripts/ssh-pi.sh` helper for consistent SSH connections
