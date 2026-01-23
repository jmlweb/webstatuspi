"""Security utilities for WebStatusπ."""

import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Blocked schemes for SSRF prevention
BLOCKED_SCHEMES = ["file", "ftp", "gopher", "data", "dict", "ldap", "telnet"]

# Blocked ports (common internal services)
BLOCKED_PORTS = [
    22,  # SSH
    23,  # Telnet
    25,  # SMTP
    3306,  # MySQL
    5432,  # PostgreSQL
    6379,  # Redis
    27017,  # MongoDB
    9200,  # Elasticsearch
    9300,  # Elasticsearch
]

# Private IP ranges to block
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("169.254.0.0/16"),  # Cloud metadata (AWS, etc.)
]


class SSRFError(Exception):
    """Raised when a URL fails SSRF validation."""

    pass


def validate_url_for_ssrf(url: str, allow_private: bool = False) -> None:
    """Validate URL to prevent SSRF attacks.

    Args:
        url: The URL to validate
        allow_private: If True, allow private IPs (for testing only)

    Raises:
        SSRFError: If URL is potentially dangerous
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        raise SSRFError(f"Invalid URL format: {e}")

    # Only allow HTTP/HTTPS
    if parsed.scheme not in ("http", "https"):
        raise SSRFError(f"Scheme '{parsed.scheme}' not allowed. Only http:// and https:// are permitted.")

    # Block known dangerous ports
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as e:
        raise SSRFError(f"Invalid port in URL: {e}")

    if port in BLOCKED_PORTS:
        raise SSRFError(f"Port {port} is blocked for security reasons")

    # Validate hostname exists
    hostname = parsed.hostname
    if not hostname:
        raise SSRFError("No hostname in URL")

    # Block localhost variations (case-insensitive)
    localhost_names = {
        "localhost",
        "127.0.0.1",
        "::1",
        "0.0.0.0",
        "localhost.localdomain",
        "ip6-localhost",
        "ip6-loopback",
    }
    if hostname.lower() in localhost_names:
        raise SSRFError(f"Localhost access not allowed: {hostname}")

    if allow_private:
        return  # Skip IP validation for testing

    # Resolve hostname and check for private IPs
    try:
        ip = socket.gethostbyname(hostname)
        ip_obj = ipaddress.ip_address(ip)

        # Check against private IP ranges
        for private_range in PRIVATE_IP_RANGES:
            if ip_obj in private_range:
                raise SSRFError(f"Private IP address not allowed: {ip} (resolved from {hostname})")

        # Additional check for multicast/reserved
        if ip_obj.is_multicast or ip_obj.is_reserved:
            raise SSRFError(f"Reserved IP address not allowed: {ip}")

    except socket.gaierror as e:
        raise SSRFError(f"Cannot resolve hostname '{hostname}': {e}")
    except SSRFError:
        # Re-raise SSRFError as-is
        raise
    except Exception as e:
        raise SSRFError(f"URL validation failed: {e}")


def validate_url_name(name: str) -> str | None:
    """Validate and sanitize URL name from user input.

    Args:
        name: Raw URL name

    Returns:
        Validated name if safe, None if invalid
    """
    if not name or not isinstance(name, str):
        return None

    # Reject path traversal sequences
    if ".." in name or "/" in name or "\\" in name:
        logger.warning("Path traversal attempt in URL name: %s", name)
        return None

    # Reject null bytes and control characters
    if "\x00" in name or any(ord(c) < 32 and c not in "\t\n\r" for c in name):
        logger.warning("Control characters in URL name: %s", name)
        return None

    # URL names limited to 10 chars (OLED display constraint)
    if len(name) > 10:
        logger.warning("URL name too long: %s", name)
        return None

    # Only allow alphanumerics, hyphens, underscores
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        logger.warning("Invalid characters in URL name: %s", name)
        return None

    return name
