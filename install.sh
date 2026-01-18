#!/usr/bin/env bash
# WebStatusPi Installer
# https://github.com/jmlweb/webstatuspi
#
# Usage:
#   curl -sSL https://raw.githubusercontent.com/jmlweb/webstatuspi/main/install.sh | bash
#   ./install.sh [options]
#
# Options:
#   --install-dir DIR    Installation directory
#   --port PORT          API port (default: 8080)
#   --uninstall          Uninstall WebStatusPi
#   --update             Update existing installation
#   --non-interactive    Non-interactive mode (use defaults)
#   -h, --help           Show help

set -euo pipefail

# ==============================================================================
# Constants
# ==============================================================================

INSTALLER_VERSION="1.0.0"
GITHUB_REPO="jmlweb/webstatuspi"
GITHUB_URL="https://github.com/${GITHUB_REPO}.git"
MIN_PYTHON_VERSION="3.7"
DEFAULT_INSTALL_DIR="/opt/webstatuspi"
DEFAULT_USER_INSTALL_DIR="${HOME}/webstatuspi"
DEFAULT_PORT=8080
DEFAULT_INTERVAL=60
SERVICE_NAME="webstatuspi"

# File descriptor for user input (handles curl | bash case)
INPUT_FD=0

# ==============================================================================
# Colors and Formatting
# ==============================================================================

setup_colors() {
    if [[ -t 1 ]] && [[ -z "${NO_COLOR:-}" ]] && command -v tput &>/dev/null; then
        BOLD=$(tput bold)
        RED=$(tput setaf 1)
        GREEN=$(tput setaf 2)
        YELLOW=$(tput setaf 3)
        BLUE=$(tput setaf 4)
        MAGENTA=$(tput setaf 5)
        CYAN=$(tput setaf 6)
        RESET=$(tput sgr0)
    else
        BOLD=""
        RED=""
        GREEN=""
        YELLOW=""
        BLUE=""
        MAGENTA=""
        CYAN=""
        RESET=""
    fi
}

# ==============================================================================
# Logging Functions
# ==============================================================================

info() {
    echo "${BLUE}[INFO]${RESET} $*"
}

warn() {
    echo "${YELLOW}[WARN]${RESET} $*" >&2
}

error() {
    echo "${RED}[ERROR]${RESET} $*" >&2
}

success() {
    echo "${GREEN}[OK]${RESET} $*"
}

step() {
    echo ""
    echo "${BOLD}${CYAN}==> $*${RESET}"
}

# ==============================================================================
# Interactive Prompts
# ==============================================================================

# Setup input for interactive prompts (handles curl | bash case)
setup_input() {
    if [[ ! -t 0 ]]; then
        # stdin is not a terminal (likely piped from curl)
        if [[ -e /dev/tty ]]; then
            # Open /dev/tty for reading user input
            exec 3</dev/tty
            INPUT_FD=3
        else
            # No tty available, force non-interactive mode
            warn "No terminal available, switching to non-interactive mode"
            NON_INTERACTIVE=true
        fi
    fi
}

# Read a line from user (handles curl | bash case)
read_input() {
    if [[ "$INPUT_FD" -eq 3 ]]; then
        read "$@" <&3
    else
        read "$@"
    fi
}

ask_yes_no() {
    local prompt="$1"
    local default="${2:-y}"
    local response

    if [[ "$NON_INTERACTIVE" == "true" ]]; then
        [[ "$default" == "y" ]]
        return $?
    fi

    if [[ "$default" == "y" ]]; then
        prompt="$prompt [Y/n]: "
    else
        prompt="$prompt [y/N]: "
    fi

    printf "%s" "$prompt"
    read_input -r response
    response="${response:-$default}"
    [[ "$response" =~ ^[Yy] ]]
}

ask_input() {
    local prompt="$1"
    local default="$2"
    local response

    if [[ "$NON_INTERACTIVE" == "true" ]]; then
        echo "$default"
        return
    fi

    printf "%s [%s]: " "$prompt" "$default"
    read_input -r response
    echo "${response:-$default}"
}

# ==============================================================================
# Utility Functions
# ==============================================================================

command_exists() {
    command -v "$1" &>/dev/null
}

require_command() {
    local cmd="$1"
    local pkg="${2:-$1}"

    if ! command_exists "$cmd"; then
        error "'$cmd' is required but not installed."
        error "Please install it with: sudo apt install $pkg"
        exit 1
    fi
}

# Compare versions: returns 0 if $1 >= $2
version_ge() {
    local v1="$1"
    local v2="$2"

    # Split versions into arrays
    IFS='.' read -ra v1_parts <<< "$v1"
    IFS='.' read -ra v2_parts <<< "$v2"

    # Compare each part
    local max_parts=${#v1_parts[@]}
    [[ ${#v2_parts[@]} -gt $max_parts ]] && max_parts=${#v2_parts[@]}

    for ((i = 0; i < max_parts; i++)); do
        local p1="${v1_parts[i]:-0}"
        local p2="${v2_parts[i]:-0}"

        if ((p1 > p2)); then
            return 0
        elif ((p1 < p2)); then
            return 1
        fi
    done

    return 0
}

get_python_version() {
    local python_cmd="$1"
    "$python_cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null
}

detect_python() {
    local python_cmd=""

    # Try python3 first, then python
    for cmd in python3 python; do
        if command_exists "$cmd"; then
            local version
            version=$(get_python_version "$cmd")
            if version_ge "$version" "$MIN_PYTHON_VERSION"; then
                python_cmd="$cmd"
                break
            fi
        fi
    done

    echo "$python_cmd"
}

is_raspberry_pi() {
    if [[ -f /proc/device-tree/model ]]; then
        grep -qi "raspberry pi" /proc/device-tree/model 2>/dev/null
        return $?
    fi
    return 1
}

has_systemd() {
    command_exists systemctl && [[ -d /run/systemd/system ]]
}

is_root() {
    [[ $EUID -eq 0 ]]
}

# ==============================================================================
# Banner
# ==============================================================================

show_banner() {
    echo ""
    echo "${CYAN}${BOLD}"
    cat << 'EOF'
 __          __  _     _____ _        _             _____ _
 \ \        / / | |   / ____| |      | |           |  __ (_)
  \ \  /\  / /__| |__| (___ | |_ __ _| |_ _   _ ___| |__) |
   \ \/  \/ / _ \ '_ \\___ \| __/ _` | __| | | / __|  ___/ |
    \  /\  /  __/ |_) |___) | || (_| | |_| |_| \__ \ |   | |
     \/  \/ \___|_.__/_____/ \__\__,_|\__|\__,_|___/_|   |_|
EOF
    echo "${RESET}"
    echo "  ${MAGENTA}Lightweight URL Monitor for Raspberry Pi${RESET}"
    echo "  ${BLUE}Installer v${INSTALLER_VERSION}${RESET}"
    echo ""
}

# ==============================================================================
# Help
# ==============================================================================

show_help() {
    cat << EOF
${BOLD}WebStatusPi Installer${RESET}

${BOLD}Usage:${RESET}
  $0 [options]

${BOLD}Options:${RESET}
  --install-dir DIR    Installation directory (default: ${DEFAULT_USER_INSTALL_DIR})
  --port PORT          API port (default: ${DEFAULT_PORT})
  --uninstall          Uninstall WebStatusPi
  --update             Update existing installation
  --non-interactive    Non-interactive mode (use defaults)
  -h, --help           Show this help message

${BOLD}Examples:${RESET}
  $0                           # Interactive installation
  $0 --non-interactive         # Install with defaults
  sudo $0 --install-dir /opt/webstatuspi  # System-wide installation
  $0 --uninstall               # Remove installation
  $0 --update                  # Update existing installation

${BOLD}One-liner installation:${RESET}
  curl -sSL https://raw.githubusercontent.com/jmlweb/webstatuspi/main/install.sh | bash

EOF
}

# ==============================================================================
# Pre-flight Checks
# ==============================================================================

check_prerequisites() {
    step "Checking prerequisites"

    # Detect Raspberry Pi (informational)
    if is_raspberry_pi; then
        success "Running on Raspberry Pi"
    else
        info "Not running on Raspberry Pi (installation will proceed)"
    fi

    # Check git
    if command_exists git; then
        success "git is installed"
    else
        error "git is required but not installed"
        error "Install with: sudo apt install git"
        exit 1
    fi

    # Check Python
    PYTHON_CMD=$(detect_python)
    if [[ -z "$PYTHON_CMD" ]]; then
        error "Python ${MIN_PYTHON_VERSION}+ is required but not found"
        error "Install with: sudo apt install python3"
        exit 1
    fi

    local python_version
    python_version=$(get_python_version "$PYTHON_CMD")
    success "Python $python_version found ($PYTHON_CMD)"

    # Check venv module
    if "$PYTHON_CMD" -c "import venv" 2>/dev/null; then
        success "Python venv module available"
    else
        error "Python venv module is required but not installed"
        error "Install with: sudo apt install python3-venv"
        exit 1
    fi

    # Check pip
    if "$PYTHON_CMD" -m pip --version &>/dev/null; then
        success "pip is available"
    else
        error "pip is required but not installed"
        error "Install with: sudo apt install python3-pip"
        exit 1
    fi

    # Check systemd (optional)
    if has_systemd; then
        success "systemd detected (service installation available)"
        HAS_SYSTEMD=true
    else
        info "systemd not detected (service installation unavailable)"
        HAS_SYSTEMD=false
    fi
}

# ==============================================================================
# Installation
# ==============================================================================

select_install_dir() {
    step "Selecting installation directory"

    if [[ -n "${OPT_INSTALL_DIR:-}" ]]; then
        INSTALL_DIR="$OPT_INSTALL_DIR"
        info "Using specified directory: $INSTALL_DIR"
        return
    fi

    if [[ "$NON_INTERACTIVE" == "true" ]]; then
        if is_root; then
            INSTALL_DIR="$DEFAULT_INSTALL_DIR"
        else
            INSTALL_DIR="$DEFAULT_USER_INSTALL_DIR"
        fi
        info "Using default directory: $INSTALL_DIR"
        return
    fi

    echo ""
    echo "Where would you like to install WebStatusPi?"
    echo ""
    echo "  1) ${DEFAULT_USER_INSTALL_DIR} (user installation)"
    if is_root; then
        echo "  2) ${DEFAULT_INSTALL_DIR} (system installation) ${GREEN}[recommended]${RESET}"
    else
        echo "  2) ${DEFAULT_INSTALL_DIR} (requires sudo)"
    fi
    echo "  3) Custom directory"
    echo ""

    printf "Select option [1]: "
    read_input -r choice
    choice="${choice:-1}"

    case "$choice" in
        1)
            INSTALL_DIR="$DEFAULT_USER_INSTALL_DIR"
            ;;
        2)
            INSTALL_DIR="$DEFAULT_INSTALL_DIR"
            if ! is_root; then
                warn "System installation requires root privileges"
                error "Please run with: sudo $0"
                exit 1
            fi
            ;;
        3)
            printf "Enter installation directory: "
            read_input -r INSTALL_DIR
            if [[ -z "$INSTALL_DIR" ]]; then
                error "Installation directory cannot be empty"
                exit 1
            fi
            ;;
        *)
            INSTALL_DIR="$DEFAULT_USER_INSTALL_DIR"
            ;;
    esac

    info "Installation directory: $INSTALL_DIR"
}

clone_or_update_repo() {
    step "Getting WebStatusPi source code"

    if [[ -d "$INSTALL_DIR/.git" ]]; then
        info "Existing installation found, updating..."

        # Backup config if exists
        if [[ -f "$INSTALL_DIR/config.yaml" ]]; then
            local backup="$INSTALL_DIR/config.yaml.backup.$(date +%Y%m%d_%H%M%S)"
            cp "$INSTALL_DIR/config.yaml" "$backup"
            success "Configuration backed up to $backup"
        fi

        cd "$INSTALL_DIR"
        git fetch origin
        git reset --hard origin/main
        success "Repository updated to latest version"
    else
        # Create parent directory if needed
        local parent_dir
        parent_dir=$(dirname "$INSTALL_DIR")
        if [[ ! -d "$parent_dir" ]]; then
            mkdir -p "$parent_dir"
        fi

        info "Cloning repository..."
        git clone "$GITHUB_URL" "$INSTALL_DIR"
        success "Repository cloned to $INSTALL_DIR"
    fi

    cd "$INSTALL_DIR"
}

setup_virtualenv() {
    step "Setting up Python virtual environment"

    local venv_dir="$INSTALL_DIR/venv"

    if [[ -d "$venv_dir" ]]; then
        info "Virtual environment exists, upgrading..."
    else
        info "Creating virtual environment..."
        "$PYTHON_CMD" -m venv "$venv_dir"
    fi

    # Activate and upgrade pip
    source "$venv_dir/bin/activate"
    pip install --upgrade pip --quiet

    success "Virtual environment ready at $venv_dir"
}

install_dependencies() {
    step "Installing dependencies"

    cd "$INSTALL_DIR"
    source "$INSTALL_DIR/venv/bin/activate"

    info "Installing WebStatusPi in editable mode..."
    pip install -e . --quiet

    success "Dependencies installed"

    # Verify installation
    if webstatuspi --version &>/dev/null; then
        local version
        version=$(webstatuspi --version)
        success "WebStatusPi installed: $version"
    else
        error "Installation verification failed"
        exit 1
    fi
}

# ==============================================================================
# Configuration
# ==============================================================================

configure_webstatuspi() {
    step "Configuring WebStatusPi"

    local config_file="$INSTALL_DIR/config.yaml"

    # Check if config already exists
    if [[ -f "$config_file" ]]; then
        if ask_yes_no "Configuration file exists. Keep existing configuration?" "y"; then
            success "Keeping existing configuration"
            return
        fi
    fi

    # Get configuration values
    local port
    local interval

    if [[ -n "${OPT_PORT:-}" ]]; then
        port="$OPT_PORT"
    else
        port=$(ask_input "API port" "$DEFAULT_PORT")
    fi

    interval=$(ask_input "Monitor interval (seconds)" "$DEFAULT_INTERVAL")

    # Get URLs to monitor
    local urls=()
    local url_configs=""

    if [[ "$NON_INTERACTIVE" == "true" ]]; then
        info "Using example URLs (edit config.yaml to customize)"
        url_configs='  - name: "GOOGLE"
    url: "https://www.google.com"
    timeout: 5

  - name: "GITHUB"
    url: "https://github.com"
    timeout: 10'
    else
        echo ""
        echo "Configure URLs to monitor."
        echo "Format: NAME URL [TIMEOUT]"
        echo "  NAME: Short identifier (max 10 chars, e.g., MY_APP)"
        echo "  URL: Full URL to monitor"
        echo "  TIMEOUT: Optional request timeout in seconds (default: 10)"
        echo ""
        echo "Enter URLs one per line. Empty line to finish."
        echo ""

        local count=0
        while true; do
            printf "URL %d: " "$((count + 1))"
            read_input -r line

            [[ -z "$line" ]] && break

            # Parse the line
            local name url timeout
            read -r name url timeout <<< "$line"

            if [[ -z "$name" ]] || [[ -z "$url" ]]; then
                warn "Invalid format. Use: NAME URL [TIMEOUT]"
                continue
            fi

            # Validate URL
            if [[ ! "$url" =~ ^https?:// ]]; then
                warn "URL must start with http:// or https://"
                continue
            fi

            # Build URL config
            url_configs+="  - name: \"$name\"
    url: \"$url\""

            if [[ -n "$timeout" ]]; then
                url_configs+="
    timeout: $timeout"
            fi

            url_configs+=$'\n\n'
            ((count++))
        done

        if [[ $count -eq 0 ]]; then
            info "No URLs configured, using examples"
            url_configs='  - name: "GOOGLE"
    url: "https://www.google.com"
    timeout: 5

  - name: "GITHUB"
    url: "https://github.com"
    timeout: 10'
        else
            # Remove trailing newlines
            url_configs="${url_configs%$'\n\n'}"
        fi
    fi

    # Generate config file
    cat > "$config_file" << EOF
# WebStatusPi Configuration
# Generated by installer on $(date)

monitor:
  interval: ${interval}

urls:
${url_configs}

database:
  path: "./data/status.db"
  retention_days: 7

display:
  enabled: true
  cycle_interval: 5

api:
  enabled: true
  port: ${port}
EOF

    success "Configuration saved to $config_file"

    # Create data directory
    mkdir -p "$INSTALL_DIR/data"
}

# ==============================================================================
# Systemd Service
# ==============================================================================

install_systemd_service() {
    if [[ "$HAS_SYSTEMD" != "true" ]]; then
        return
    fi

    step "Systemd Service"

    if [[ "$NON_INTERACTIVE" == "true" ]]; then
        if is_root; then
            info "Installing systemd service..."
        else
            info "Skipping service installation (requires root)"
            return
        fi
    else
        if ! ask_yes_no "Install systemd service for auto-start?" "y"; then
            info "Skipping service installation"
            return
        fi
    fi

    if ! is_root; then
        warn "Service installation requires root privileges"
        echo ""
        echo "To install the service manually, run:"
        echo "  cd $INSTALL_DIR"
        echo "  source venv/bin/activate"
        echo "  sudo webstatuspi install-service --enable --start"
        echo ""
        return
    fi

    # Use the built-in install-service command
    cd "$INSTALL_DIR"
    source "$INSTALL_DIR/venv/bin/activate"

    if webstatuspi install-service --enable --start; then
        success "Systemd service installed and started"
    else
        error "Failed to install systemd service"
    fi
}

# ==============================================================================
# Post-Installation Verification
# ==============================================================================

verify_installation() {
    step "Verifying installation"

    cd "$INSTALL_DIR"
    source "$INSTALL_DIR/venv/bin/activate"

    # Check command
    if webstatuspi --version &>/dev/null; then
        local version
        version=$(webstatuspi --version)
        success "Command available: $version"
    else
        error "webstatuspi command not working"
        exit 1
    fi

    # Check service if installed
    if [[ "$HAS_SYSTEMD" == "true" ]] && is_root; then
        if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
            success "Service is running"

            # Wait a moment for API to start
            sleep 2

            # Test API
            local port
            port=$(grep -oP 'port:\s*\K\d+' "$INSTALL_DIR/config.yaml" 2>/dev/null || echo "$DEFAULT_PORT")

            if curl -s "http://localhost:${port}/status" &>/dev/null; then
                success "API responding at http://localhost:${port}"
            else
                warn "API not responding yet (may still be starting)"
            fi
        fi
    fi
}

# ==============================================================================
# Completion Message
# ==============================================================================

show_completion() {
    step "Installation Complete!"

    local port
    port=$(grep -oP 'port:\s*\K\d+' "$INSTALL_DIR/config.yaml" 2>/dev/null || echo "$DEFAULT_PORT")

    echo ""
    echo "${GREEN}${BOLD}WebStatusPi has been installed successfully!${RESET}"
    echo ""
    echo "${BOLD}Installation directory:${RESET} $INSTALL_DIR"
    echo "${BOLD}Configuration file:${RESET} $INSTALL_DIR/config.yaml"
    echo ""
    echo "${BOLD}Quick Start:${RESET}"
    echo ""

    if [[ "$HAS_SYSTEMD" == "true" ]] && systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        echo "  The service is running. Access the dashboard at:"
        echo "  ${CYAN}http://localhost:${port}${RESET}"
        echo ""
        echo "  Useful commands:"
        echo "    sudo systemctl status ${SERVICE_NAME}   # Check status"
        echo "    sudo journalctl -u ${SERVICE_NAME} -f   # View logs"
        echo "    sudo systemctl restart ${SERVICE_NAME}  # Restart"
    else
        echo "  To start WebStatusPi manually:"
        echo ""
        echo "    cd $INSTALL_DIR"
        echo "    source venv/bin/activate"
        echo "    webstatuspi run"
        echo ""
        echo "  Then access the dashboard at:"
        echo "  ${CYAN}http://localhost:${port}${RESET}"

        if [[ "$HAS_SYSTEMD" == "true" ]] && ! is_root; then
            echo ""
            echo "  To install as a service (auto-start on boot):"
            echo "    cd $INSTALL_DIR"
            echo "    source venv/bin/activate"
            echo "    sudo webstatuspi install-service --enable --start"
        fi
    fi

    echo ""
    echo "${BOLD}Documentation:${RESET}"
    echo "  https://github.com/${GITHUB_REPO}"
    echo ""
}

# ==============================================================================
# Uninstallation
# ==============================================================================

uninstall() {
    show_banner

    step "Uninstalling WebStatusPi"

    # Find installation directory
    local install_dir=""

    if [[ -n "${OPT_INSTALL_DIR:-}" ]]; then
        install_dir="$OPT_INSTALL_DIR"
    elif [[ -d "$DEFAULT_INSTALL_DIR" ]]; then
        install_dir="$DEFAULT_INSTALL_DIR"
    elif [[ -d "$DEFAULT_USER_INSTALL_DIR" ]]; then
        install_dir="$DEFAULT_USER_INSTALL_DIR"
    else
        error "No WebStatusPi installation found"
        exit 1
    fi

    info "Found installation at: $install_dir"

    if [[ "$NON_INTERACTIVE" != "true" ]]; then
        if ! ask_yes_no "Are you sure you want to uninstall WebStatusPi?" "n"; then
            info "Uninstallation cancelled"
            exit 0
        fi
    fi

    # Stop and remove systemd service
    if has_systemd && systemctl list-unit-files "$SERVICE_NAME.service" &>/dev/null; then
        info "Stopping and removing systemd service..."

        if is_root; then
            systemctl stop "$SERVICE_NAME" 2>/dev/null || true
            systemctl disable "$SERVICE_NAME" 2>/dev/null || true
            rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
            systemctl daemon-reload
            success "Systemd service removed"
        else
            warn "Cannot remove systemd service without root privileges"
            echo "  Run: sudo systemctl stop ${SERVICE_NAME}"
            echo "  Run: sudo systemctl disable ${SERVICE_NAME}"
            echo "  Run: sudo rm /etc/systemd/system/${SERVICE_NAME}.service"
        fi
    fi

    # Backup config and data
    if [[ -f "$install_dir/config.yaml" ]] || [[ -d "$install_dir/data" ]]; then
        local backup_dir="${HOME}/webstatuspi_backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$backup_dir"

        [[ -f "$install_dir/config.yaml" ]] && cp "$install_dir/config.yaml" "$backup_dir/"
        [[ -d "$install_dir/data" ]] && cp -r "$install_dir/data" "$backup_dir/"

        success "Configuration and data backed up to $backup_dir"
    fi

    # Remove installation directory
    if [[ -d "$install_dir" ]]; then
        rm -rf "$install_dir"
        success "Removed $install_dir"
    fi

    echo ""
    success "WebStatusPi has been uninstalled"
    echo ""
}

# ==============================================================================
# Update
# ==============================================================================

update() {
    show_banner

    step "Updating WebStatusPi"

    # Find installation directory
    local install_dir=""

    if [[ -n "${OPT_INSTALL_DIR:-}" ]]; then
        install_dir="$OPT_INSTALL_DIR"
    elif [[ -d "$DEFAULT_INSTALL_DIR" ]]; then
        install_dir="$DEFAULT_INSTALL_DIR"
    elif [[ -d "$DEFAULT_USER_INSTALL_DIR" ]]; then
        install_dir="$DEFAULT_USER_INSTALL_DIR"
    else
        error "No WebStatusPi installation found"
        error "Run without --update to perform fresh installation"
        exit 1
    fi

    INSTALL_DIR="$install_dir"
    info "Found installation at: $INSTALL_DIR"

    # Stop service if running
    local restart_service=false
    if has_systemd && systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        if is_root; then
            info "Stopping service for update..."
            systemctl stop "$SERVICE_NAME"
            restart_service=true
        else
            warn "Service is running but we don't have root to stop it"
            warn "Please stop the service manually before updating"
        fi
    fi

    # Update repository
    clone_or_update_repo

    # Reinstall in venv
    setup_virtualenv
    install_dependencies

    # Restart service if we stopped it
    if [[ "$restart_service" == "true" ]]; then
        info "Restarting service..."
        systemctl start "$SERVICE_NAME"
        success "Service restarted"
    fi

    verify_installation

    echo ""
    success "WebStatusPi has been updated!"
    echo ""
}

# ==============================================================================
# Main
# ==============================================================================

main() {
    # Initialize
    setup_colors

    # Parse arguments
    NON_INTERACTIVE=false
    OPT_INSTALL_DIR=""
    OPT_PORT=""
    ACTION="install"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --install-dir)
                OPT_INSTALL_DIR="$2"
                shift 2
                ;;
            --port)
                OPT_PORT="$2"
                shift 2
                ;;
            --uninstall)
                ACTION="uninstall"
                shift
                ;;
            --update)
                ACTION="update"
                shift
                ;;
            --non-interactive)
                NON_INTERACTIVE=true
                shift
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done

    # Setup input handling (for curl | bash case)
    setup_input

    # Execute action
    case "$ACTION" in
        uninstall)
            uninstall
            ;;
        update)
            update
            ;;
        install)
            show_banner
            check_prerequisites
            select_install_dir
            clone_or_update_repo
            setup_virtualenv
            install_dependencies
            configure_webstatuspi
            install_systemd_service
            verify_installation
            show_completion
            ;;
    esac
}

main "$@"
