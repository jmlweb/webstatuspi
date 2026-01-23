"""Systemd service installation for WebStatusπ."""

import getpass
import os
import subprocess
import sys
from pathlib import Path

SERVICE_NAME = "webstatuspi"
SERVICE_PATH = Path("/etc/systemd/system/webstatuspi.service")

SERVICE_TEMPLATE = """\
[Unit]
Description=WebStatusπ URL Monitor
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User={user}
WorkingDirectory={working_dir}
ExecStart={python_path} -m webstatuspi run
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
"""


def detect_paths() -> dict:
    """Detect default paths for service configuration."""
    return {
        "user": getpass.getuser(),
        "working_dir": os.getcwd(),
        "python_path": sys.executable,
    }


def generate_service_file(user: str, working_dir: str, python_path: str) -> str:
    """Generate the systemd service file content."""
    return SERVICE_TEMPLATE.format(
        user=user,
        working_dir=working_dir,
        python_path=python_path,
    )


def install_service(
    user: str,
    working_dir: str,
    python_path: str,
    enable: bool = False,
    start: bool = False,
    dry_run: bool = False,
) -> bool:
    """Install the systemd service file.

    Returns True if successful, False otherwise.
    """
    content = generate_service_file(user, working_dir, python_path)

    print("Generated service file:")
    print("-" * 40)
    print(content)
    print("-" * 40)

    if dry_run:
        print("\n[Dry run] Service file not installed.")
        return True

    # Check if we have write permissions
    if not _has_root_permissions():
        print(f"\nError: Cannot write to {SERVICE_PATH}")
        print("Run with sudo: sudo webstatuspi install-service")
        return False

    # Write service file
    try:
        SERVICE_PATH.write_text(content)
        print(f"\nService file written to {SERVICE_PATH}")
    except PermissionError:
        print(f"\nError: Permission denied writing to {SERVICE_PATH}")
        print("Run with sudo: sudo webstatuspi install-service")
        return False
    except OSError as e:
        print(f"\nError writing service file: {e}")
        return False

    # Reload systemd
    if not _run_systemctl("daemon-reload"):
        return False
    print("Systemd daemon reloaded")

    # Enable service if requested
    if enable:
        if not _run_systemctl("enable", SERVICE_NAME):
            return False
        print(f"Service {SERVICE_NAME} enabled for auto-start")

    # Start service if requested
    if start:
        if not _run_systemctl("start", SERVICE_NAME):
            return False
        print(f"Service {SERVICE_NAME} started")

    print("\nInstallation complete!")
    print("\nUseful commands:")
    print(f"  sudo systemctl status {SERVICE_NAME}   # Check status")
    print(f"  sudo journalctl -u {SERVICE_NAME} -f   # View logs")
    print(f"  sudo systemctl restart {SERVICE_NAME}  # Restart service")

    return True


def _has_root_permissions() -> bool:
    """Check if we have root permissions."""
    return os.geteuid() == 0


def _run_systemctl(*args: str) -> bool:
    """Run a systemctl command."""
    cmd = ["systemctl", *args]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {' '.join(cmd)}: {e.stderr}")
        return False
    except FileNotFoundError:
        print("Error: systemctl not found. Is systemd installed?")
        return False
