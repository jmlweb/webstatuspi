#!/usr/bin/env bash
#
# SSH helper script for connecting to Raspberry Pi
# Uses environment variables from .env.local
#
# Usage:
#   ./scripts/ssh-pi.sh              # Interactive SSH session
#   ./scripts/ssh-pi.sh "command"    # Execute remote command
#   ./scripts/ssh-pi.sh -y "command" # Skip confirmation prompt
#
# Security:
#   - Requires SSH key authentication (no passwords)
#   - Validates key access before connecting
#   - Confirmation prompt for interactive sessions
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env.local"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Parse flags
SKIP_CONFIRM=false
while getopts "y" opt; do
    case $opt in
        y) SKIP_CONFIRM=true ;;
        *) ;;
    esac
done
shift $((OPTIND-1))

# Load environment variables
if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${RED}Error: $ENV_FILE not found${NC}" >&2
    echo "" >&2
    echo "Create it from the template:" >&2
    echo "  cp .env.local.example .env.local" >&2
    echo "  # Edit .env.local with your values" >&2
    exit 1
fi

# shellcheck source=/dev/null
source "$ENV_FILE"

# Validate required variables
required_vars=("PI_SSH_HOST" "PI_SSH_USER")
for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        echo -e "${RED}Error: $var is not set in $ENV_FILE${NC}" >&2
        exit 1
    fi
done

# Default port if not set
PI_SSH_PORT="${PI_SSH_PORT:-22}"

# Build SSH target
SSH_TARGET="${PI_SSH_USER}@${PI_SSH_HOST}"
SSH_OPTS=(-p "$PI_SSH_PORT" -o "BatchMode=yes" -o "ConnectTimeout=10")

# Validate SSH key authentication is configured
validate_ssh_key() {
    echo -e "${YELLOW}Validating SSH key access...${NC}"

    if ! ssh "${SSH_OPTS[@]}" "$SSH_TARGET" "exit" 2>/dev/null; then
        echo -e "${RED}Error: SSH key authentication failed${NC}" >&2
        echo "" >&2
        echo "Password authentication is not supported for security reasons." >&2
        echo "" >&2
        echo "To set up SSH key authentication:" >&2
        echo "  1. Generate a key (if you don't have one):" >&2
        echo "     ssh-keygen -t ed25519 -C \"claude-deploy\"" >&2
        echo "" >&2
        echo "  2. Copy your key to the Pi:" >&2
        echo "     ssh-copy-id -p $PI_SSH_PORT $SSH_TARGET" >&2
        echo "" >&2
        echo "  3. Test the connection:" >&2
        echo "     ssh -p $PI_SSH_PORT $SSH_TARGET" >&2
        echo "" >&2
        exit 1
    fi

    echo -e "${GREEN}SSH key validation successful${NC}"
}

# Confirmation prompt for interactive sessions
confirm_connection() {
    if [[ "$SKIP_CONFIRM" == "true" ]]; then
        return 0
    fi

    echo ""
    echo -e "Target: ${GREEN}$SSH_TARGET${NC} (port $PI_SSH_PORT)"
    echo ""
    read -r -p "Connect to this host? [y/N] " response
    case "$response" in
        [yY][eE][sS]|[yY])
            return 0
            ;;
        *)
            echo "Connection cancelled."
            exit 0
            ;;
    esac
}

# Main execution
validate_ssh_key

# Remove BatchMode for actual connection (allows interactive use)
SSH_OPTS_INTERACTIVE=(-p "$PI_SSH_PORT")

if [[ $# -eq 0 ]]; then
    # Interactive session - ask for confirmation
    confirm_connection
    echo -e "${GREEN}Connecting to $SSH_TARGET...${NC}"
    exec ssh "${SSH_OPTS_INTERACTIVE[@]}" "$SSH_TARGET"
else
    # Execute command - no confirmation needed for automation
    exec ssh "${SSH_OPTS_INTERACTIVE[@]}" "$SSH_TARGET" "$@"
fi
