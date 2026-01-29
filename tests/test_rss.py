"""Tests for the RSS feed module."""

import xml.etree.ElementTree as ET
from datetime import UTC, datetime

import pytest

from webstatuspi._rss import (
    _format_rfc822,
    _status_to_description,
    generate_rss_feed,
)
from webstatuspi.config import ConfigError, RssConfig
from webstatuspi.models import UrlStatus


@pytest.fixture
def sample_status() -> UrlStatus:
    """Create a sample URL status."""
    return UrlStatus(
        url_name="TEST_URL",
        url="https://example.com",
        is_up=True,
        last_status_code=200,
        last_response_time_ms=150,
        last_error=None,
        last_check=datetime(2026, 1, 28, 10, 30, 0, tzinfo=UTC),
        checks_24h=24,
        uptime_24h=99.5,
    )


@pytest.fixture
def sample_status_down() -> UrlStatus:
    """Create a sample URL status that is down."""
    return UrlStatus(
        url_name="DOWN_SVC",
        url="https://down.example.com",
        is_up=False,
        last_status_code=503,
        last_response_time_ms=5000,
        last_error="Service Unavailable",
        last_check=datetime(2026, 1, 28, 10, 25, 0, tzinfo=UTC),
        checks_24h=24,
        uptime_24h=75.0,
    )


@pytest.fixture
def default_rss_config() -> RssConfig:
    """Create default RSS configuration."""
    return RssConfig()


@pytest.fixture
def custom_rss_config() -> RssConfig:
    """Create custom RSS configuration."""
    return RssConfig(
        enabled=True,
        title="My Status Feed",
        description="Custom description",
        max_items=5,
        link="https://status.example.com",
    )


class TestRssConfig:
    """Tests for RssConfig dataclass."""

    def test_default_values(self) -> None:
        """Default RssConfig has expected values."""
        config = RssConfig()
        assert config.enabled is True
        assert config.title == "WebStatusπ Status Feed"
        assert config.description == "Real-time status updates for monitored services"
        assert config.max_items == 20
        assert config.link == ""

    def test_custom_values(self, custom_rss_config: RssConfig) -> None:
        """Custom RssConfig preserves values."""
        assert custom_rss_config.title == "My Status Feed"
        assert custom_rss_config.description == "Custom description"
        assert custom_rss_config.max_items == 5
        assert custom_rss_config.link == "https://status.example.com"

    def test_max_items_minimum(self) -> None:
        """max_items must be at least 1."""
        with pytest.raises(ConfigError, match="must be at least 1"):
            RssConfig(max_items=0)

    def test_max_items_maximum(self) -> None:
        """max_items must not exceed 100."""
        with pytest.raises(ConfigError, match="must not exceed 100"):
            RssConfig(max_items=101)


class TestFormatRfc822:
    """Tests for _format_rfc822 function."""

    def test_formats_datetime_correctly(self) -> None:
        """Datetime is formatted as RFC 822."""
        dt = datetime(2026, 1, 28, 10, 30, 0, tzinfo=UTC)
        result = _format_rfc822(dt)
        # RFC 822 format: "Tue, 28 Jan 2026 10:30:00 +0000" or similar
        assert "28 Jan 2026" in result
        assert "10:30:00" in result


class TestStatusToDescription:
    """Tests for _status_to_description function."""

    def test_up_status_description(self, sample_status: UrlStatus) -> None:
        """UP status generates correct description."""
        desc = _status_to_description(sample_status)
        assert "Status: UP" in desc
        assert "HTTP Status: 200" in desc
        assert "Response Time: 150ms" in desc
        assert "Uptime (24h): 99.5%" in desc

    def test_down_status_description(self, sample_status_down: UrlStatus) -> None:
        """DOWN status generates correct description with error."""
        desc = _status_to_description(sample_status_down)
        assert "Status: DOWN" in desc
        assert "HTTP Status: 503" in desc
        assert "Error: Service Unavailable" in desc
        assert "Uptime (24h): 75.0%" in desc

    def test_ssl_expiring_soon(self) -> None:
        """SSL certificate expiring soon is included."""
        status = UrlStatus(
            url_name="SSL_WARN",
            url="https://ssl.example.com",
            is_up=True,
            last_status_code=200,
            last_response_time_ms=100,
            last_error=None,
            last_check=datetime(2026, 1, 28, 10, 30, 0, tzinfo=UTC),
            checks_24h=24,
            uptime_24h=100.0,
            ssl_cert_expires_in_days=15,
        )
        desc = _status_to_description(status)
        assert "SSL Certificate: Expires in 15 days" in desc

    def test_ssl_expired(self) -> None:
        """Expired SSL certificate is flagged."""
        status = UrlStatus(
            url_name="SSL_EXP",
            url="https://expired.example.com",
            is_up=True,
            last_status_code=200,
            last_response_time_ms=100,
            last_error=None,
            last_check=datetime(2026, 1, 28, 10, 30, 0, tzinfo=UTC),
            checks_24h=24,
            uptime_24h=100.0,
            ssl_cert_expires_in_days=-5,
        )
        desc = _status_to_description(status)
        assert "SSL Certificate: EXPIRED (5 days ago)" in desc


class TestGenerateRssFeed:
    """Tests for generate_rss_feed function."""

    def test_generates_valid_xml(self, sample_status: UrlStatus, default_rss_config: RssConfig) -> None:
        """Generated RSS is valid XML."""
        xml_str = generate_rss_feed([sample_status], default_rss_config)
        # Should not raise
        root = ET.fromstring(xml_str)
        assert root.tag == "rss"
        assert root.attrib["version"] == "2.0"

    def test_includes_xml_declaration(self, sample_status: UrlStatus, default_rss_config: RssConfig) -> None:
        """RSS feed includes XML declaration."""
        xml_str = generate_rss_feed([sample_status], default_rss_config)
        assert xml_str.startswith("<?xml version")

    def test_channel_metadata(self, sample_status: UrlStatus, custom_rss_config: RssConfig) -> None:
        """Channel metadata is correctly set."""
        xml_str = generate_rss_feed([sample_status], custom_rss_config)
        root = ET.fromstring(xml_str)
        channel = root.find("channel")

        assert channel is not None
        assert channel.find("title").text == "My Status Feed"
        assert channel.find("description").text == "Custom description"
        assert channel.find("link").text == "https://status.example.com"
        assert channel.find("generator").text == "WebStatusπ"

    def test_item_content(self, sample_status: UrlStatus, default_rss_config: RssConfig) -> None:
        """Item contains correct content."""
        xml_str = generate_rss_feed([sample_status], default_rss_config)
        root = ET.fromstring(xml_str)
        channel = root.find("channel")
        item = channel.find("item")

        assert item is not None
        assert "✅ UP" in item.find("title").text
        assert "TEST_URL" in item.find("title").text
        assert item.find("link").text == "https://example.com"
        assert "Status: UP" in item.find("description").text
        assert item.find("guid") is not None
        assert item.find("pubDate") is not None

    def test_down_status_title(self, sample_status_down: UrlStatus, default_rss_config: RssConfig) -> None:
        """DOWN status shows correct title."""
        xml_str = generate_rss_feed([sample_status_down], default_rss_config)
        root = ET.fromstring(xml_str)
        channel = root.find("channel")
        item = channel.find("item")

        assert "❌ DOWN" in item.find("title").text

    def test_max_items_limit(self, default_rss_config: RssConfig) -> None:
        """Feed respects max_items limit."""
        # Create more statuses than max_items
        statuses = [
            UrlStatus(
                url_name=f"SVC_{i}",
                url=f"https://example{i}.com",
                is_up=True,
                last_status_code=200,
                last_response_time_ms=100,
                last_error=None,
                last_check=datetime(2026, 1, 28, 10, i, 0, tzinfo=UTC),
                checks_24h=24,
                uptime_24h=100.0,
            )
            for i in range(30)  # More than default 20
        ]
        xml_str = generate_rss_feed(statuses, default_rss_config)
        root = ET.fromstring(xml_str)
        channel = root.find("channel")
        items = channel.findall("item")

        assert len(items) == 20  # max_items default

    def test_custom_max_items(self, custom_rss_config: RssConfig) -> None:
        """Feed respects custom max_items."""
        statuses = [
            UrlStatus(
                url_name=f"SVC_{i}",
                url=f"https://example{i}.com",
                is_up=True,
                last_status_code=200,
                last_response_time_ms=100,
                last_error=None,
                last_check=datetime(2026, 1, 28, 10, i, 0, tzinfo=UTC),
                checks_24h=24,
                uptime_24h=100.0,
            )
            for i in range(10)
        ]
        xml_str = generate_rss_feed(statuses, custom_rss_config)
        root = ET.fromstring(xml_str)
        channel = root.find("channel")
        items = channel.findall("item")

        assert len(items) == 5  # custom max_items

    def test_sorted_by_last_check(self, default_rss_config: RssConfig) -> None:
        """Items are sorted by last_check descending."""
        statuses = [
            UrlStatus(
                url_name="OLD",
                url="https://old.com",
                is_up=True,
                last_status_code=200,
                last_response_time_ms=100,
                last_error=None,
                last_check=datetime(2026, 1, 28, 8, 0, 0, tzinfo=UTC),
                checks_24h=24,
                uptime_24h=100.0,
            ),
            UrlStatus(
                url_name="NEW",
                url="https://new.com",
                is_up=True,
                last_status_code=200,
                last_response_time_ms=100,
                last_error=None,
                last_check=datetime(2026, 1, 28, 12, 0, 0, tzinfo=UTC),
                checks_24h=24,
                uptime_24h=100.0,
            ),
        ]
        xml_str = generate_rss_feed(statuses, default_rss_config)
        root = ET.fromstring(xml_str)
        channel = root.find("channel")
        items = channel.findall("item")

        # NEW should be first (more recent)
        assert "NEW" in items[0].find("title").text
        assert "OLD" in items[1].find("title").text

    def test_empty_statuses(self, default_rss_config: RssConfig) -> None:
        """Empty statuses list generates valid feed with no items."""
        xml_str = generate_rss_feed([], default_rss_config)
        root = ET.fromstring(xml_str)
        channel = root.find("channel")
        items = channel.findall("item")

        assert len(items) == 0
        assert channel.find("title") is not None

    def test_build_date_custom(self, sample_status: UrlStatus, default_rss_config: RssConfig) -> None:
        """Custom build_date is used in feed."""
        build_date = datetime(2026, 1, 28, 15, 0, 0, tzinfo=UTC)
        xml_str = generate_rss_feed([sample_status], default_rss_config, build_date=build_date)
        root = ET.fromstring(xml_str)
        channel = root.find("channel")
        last_build = channel.find("lastBuildDate").text

        assert "28 Jan 2026" in last_build
        assert "15:00:00" in last_build

    def test_no_link_when_empty(self, sample_status: UrlStatus) -> None:
        """No link element when config.link is empty."""
        config = RssConfig(link="")
        xml_str = generate_rss_feed([sample_status], config)
        root = ET.fromstring(xml_str)
        channel = root.find("channel")

        # link element should not exist or be empty
        link = channel.find("link")
        assert link is None or link.text == ""

    def test_guid_is_unique(self, default_rss_config: RssConfig) -> None:
        """Each item has a unique GUID."""
        statuses = [
            UrlStatus(
                url_name="SVC_A",
                url="https://a.com",
                is_up=True,
                last_status_code=200,
                last_response_time_ms=100,
                last_error=None,
                last_check=datetime(2026, 1, 28, 10, 0, 0, tzinfo=UTC),
                checks_24h=24,
                uptime_24h=100.0,
            ),
            UrlStatus(
                url_name="SVC_B",
                url="https://b.com",
                is_up=False,
                last_status_code=500,
                last_response_time_ms=200,
                last_error="Error",
                last_check=datetime(2026, 1, 28, 10, 0, 0, tzinfo=UTC),
                checks_24h=24,
                uptime_24h=50.0,
            ),
        ]
        xml_str = generate_rss_feed(statuses, default_rss_config)
        root = ET.fromstring(xml_str)
        channel = root.find("channel")
        items = channel.findall("item")
        guids = [item.find("guid").text for item in items]

        assert len(guids) == len(set(guids))  # All unique
