"""RSS 2.0 feed generation for status updates.

Provides RSS feed of recent status changes, allowing users to subscribe
via RSS readers and receive automatic notifications.
"""

import io
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from email.utils import format_datetime
from typing import TYPE_CHECKING

from .models import UrlStatus

if TYPE_CHECKING:
    from .config import RssConfig


def _format_rfc822(dt: datetime) -> str:
    """Format datetime as RFC 822 for RSS pubDate."""
    return format_datetime(dt)


def _status_to_description(status: UrlStatus) -> str:
    """Generate a human-readable description for a status entry."""
    lines = []

    # Status line
    state = "UP" if status.is_up else "DOWN"
    lines.append(f"Status: {state}")

    # Response info
    if status.last_status_code:
        lines.append(f"HTTP Status: {status.last_status_code}")
    lines.append(f"Response Time: {status.last_response_time_ms}ms")

    # Error if present
    if status.last_error:
        lines.append(f"Error: {status.last_error}")

    # Uptime stats
    lines.append(f"Uptime (24h): {status.uptime_24h:.1f}%")

    # SSL info if available
    if status.ssl_cert_expires_in_days is not None:
        days = status.ssl_cert_expires_in_days
        if days < 0:
            lines.append(f"SSL Certificate: EXPIRED ({abs(days)} days ago)")
        elif days <= 30:
            lines.append(f"SSL Certificate: Expires in {days} days")

    return "\n".join(lines)


def generate_rss_feed(
    statuses: list[UrlStatus],
    config: "RssConfig",
    build_date: datetime | None = None,
) -> str:
    """Generate an RSS 2.0 feed from status data.

    Args:
        statuses: List of current URL statuses.
        config: RSS configuration.
        build_date: Optional build date for the feed (defaults to now).

    Returns:
        RSS 2.0 XML string.
    """
    if build_date is None:
        build_date = datetime.now(UTC)

    # Create root element with RSS 2.0 namespace
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    # Channel metadata
    title = ET.SubElement(channel, "title")
    title.text = config.title

    description = ET.SubElement(channel, "description")
    description.text = config.description

    if config.link:
        link = ET.SubElement(channel, "link")
        link.text = config.link

    # Build date
    last_build = ET.SubElement(channel, "lastBuildDate")
    last_build.text = _format_rfc822(build_date)

    # Generator
    generator = ET.SubElement(channel, "generator")
    generator.text = "WebStatusπ"

    # Add items for each status (limited by max_items)
    # Sort by last_check descending to show most recent first
    sorted_statuses = sorted(statuses, key=lambda s: s.last_check, reverse=True)

    for status in sorted_statuses[: config.max_items]:
        item = ET.SubElement(channel, "item")

        # Item title shows service name and current state
        item_title = ET.SubElement(item, "title")
        state = "✅ UP" if status.is_up else "❌ DOWN"
        item_title.text = f"{status.url_name}: {state}"

        # Item link (to the monitored URL)
        item_link = ET.SubElement(item, "link")
        item_link.text = status.url

        # Description with detailed status info
        item_desc = ET.SubElement(item, "description")
        item_desc.text = _status_to_description(status)

        # Publication date
        pub_date = ET.SubElement(item, "pubDate")
        pub_date.text = _format_rfc822(status.last_check)

        # GUID for unique identification
        guid = ET.SubElement(item, "guid", isPermaLink="false")
        guid.text = f"{status.url_name}-{status.last_check.isoformat()}"

    # Generate XML string with declaration
    tree = ET.ElementTree(rss)
    output = io.BytesIO()
    tree.write(output, encoding="utf-8", xml_declaration=True)
    return output.getvalue().decode("utf-8")
