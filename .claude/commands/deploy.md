---
argument-hint: [pi-host]
description: Deploy to Raspberry Pi via SSH
model: haiku
---

# Deploy Skill

Deploy the application to a Raspberry Pi over SSH.

## Usage

- `/deploy` - Deploy to default Pi (from config)
- `/deploy pi@192.168.1.100` - Deploy to specific host

## Prerequisites

- SSH key authentication configured
- Pi accessible on network
- Target directory exists on Pi

## Workflow

### 1. Get Target Host

If no argument provided:
- Check for `PI_HOST` in environment
- Check for `.deploy.conf` file in project root
- Ask user for host if not found

Expected format: `user@hostname` or `user@ip`

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
# Files to deploy
rsync -avz --exclude='.git' \
           --exclude='__pycache__' \
           --exclude='*.pyc' \
           --exclude='.claude' \
           --exclude='venv' \
           --exclude='data/*.db' \
           ./ pi@host:/opt/webstatuspi/
```

### 5. Remote Setup (if first deploy)

```bash
ssh pi@host << 'EOF'
  cd /opt/webstatuspi

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
ssh pi@host "sudo systemctl restart webstatuspi 2>/dev/null || echo 'Service not installed'"
```

### 7. Verify Deployment

```bash
# Check if running
ssh pi@host "curl -s http://localhost:8080/api/health 2>/dev/null || echo 'API not responding'"
```

### 8. Report Status

```
✓ Deployed to pi@192.168.1.100

Files synced: 15
Service: restarted
API health: OK

Deployment log: /opt/webstatuspi/deploy.log
```

## Configuration File

Create `.deploy.conf` in project root:

```
PI_HOST=pi@192.168.1.100
PI_PATH=/opt/webstatuspi
PI_SERVICE=webstatuspi
```

## Rollback

If deployment fails:
```
❌ Deployment failed

Last working version backed up at:
/opt/webstatuspi.backup/

To rollback manually:
ssh pi@host "sudo mv /opt/webstatuspi.backup /opt/webstatuspi && sudo systemctl restart webstatuspi"
```

## Error Handling

- SSH connection failed: Check network and credentials
- Rsync failed: Check disk space on Pi
- Service restart failed: Check systemd logs
- API not responding: Check application logs
