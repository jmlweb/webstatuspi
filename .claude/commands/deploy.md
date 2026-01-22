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
- `.env.local` file configured
- Repository cloned on Pi at `$PI_PROJECT_PATH`

## Workflow

### 1. Load Configuration

```bash
source .env.local

# Validate required variables
if [[ -z "$PI_SSH_HOST" || -z "$PI_SSH_USER" ]]; then
    echo "Error: Configure .env.local first"
    exit 1
fi

PI_PROJECT_PATH="${PI_PROJECT_PATH:-/home/pi/webstatuspi}"
PI_SERVICE_NAME="${PI_SERVICE_NAME:-webstatuspi}"
```

### 2. Validate Local State

```bash
# Check for uncommitted changes
git status --porcelain
```

If uncommitted changes:
```
⚠️ Uncommitted changes detected - these won't be deployed

Options:
1. Commit first (/commit)
2. Continue anyway (only pushed commits will deploy)
3. Abort
```

### 3. Ensure Changes Are Pushed

```bash
# Check if local is ahead of remote
git status -sb
```

If ahead of remote:
```
⚠️ You have unpushed commits

Push now? (yes/no)
```

If yes: `git push`

### 4. Deploy via Git Pull

```bash
./scripts/ssh-pi.sh << 'EOF'
cd $PI_PROJECT_PATH || exit 1

echo "📥 Pulling latest changes..."
git fetch origin
git reset --hard origin/$(git rev-parse --abbrev-ref HEAD)

echo "📦 Installing dependencies..."
if [ -f requirements.txt ]; then
    ./venv/bin/pip install -q -r requirements.txt
fi

echo "✅ Deploy complete"
git log -1 --oneline
EOF
```

### 5. Restart Service

```bash
./scripts/ssh-pi.sh "sudo systemctl restart $PI_SERVICE_NAME 2>/dev/null || echo 'Service not configured'"
```

### 6. Verify Deployment

```bash
./scripts/ssh-pi.sh "curl -s http://localhost:8080/api/health 2>/dev/null || echo 'API not responding yet...'"
```

### 7. Report Status

```
✅ Deployed to Pi

Branch: main
Commit: abc1234 feat: add new feature
Service: restarted
API: healthy
```

## First-Time Setup on Pi

If the repo isn't cloned yet on the Pi:

```bash
./scripts/ssh-pi.sh << 'EOF'
# Clone the repository
git clone https://github.com/USER/webstatuspi.git $PI_PROJECT_PATH
cd $PI_PROJECT_PATH

# Create virtual environment
python3 -m venv venv
./venv/bin/pip install -r requirements.txt

# Create data directory
mkdir -p data
EOF
```

## Error Handling

- **SSH failed**: Check `.env.local` and SSH key setup
- **Git pull failed**: Check if repo is cloned on Pi
- **Service restart failed**: Check systemd configuration
- **API not responding**: Check application logs on Pi

## Quick Deploy (After Push)

The typical workflow:

```bash
# 1. Make changes locally
# 2. Commit
/commit

# 3. Push to GitHub
git push

# 4. Deploy to Pi
/deploy
```

## Security Notes

- Uses SSH key authentication only
- No credentials in code or commits
- Git pull over HTTPS (no SSH keys needed on Pi for GitHub)
