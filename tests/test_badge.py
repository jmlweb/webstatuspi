"""Tests for the badge SVG endpoint."""

import os
import tempfile
import time
import unittest
from datetime import UTC, datetime
from http.server import HTTPServer
from threading import Thread
from urllib.request import Request, urlopen
from xml.etree import ElementTree

from webstatuspi.api import (
    _create_handler_class,
    _generate_badge_svg,
)
from webstatuspi.database import _status_cache, init_db, insert_check
from webstatuspi.models import CheckResult


class TestBadgeSvgGeneration(unittest.TestCase):
    """Tests for _generate_badge_svg function."""

    def test_generate_badge_up_state(self):
        """Badge with 'up' state should have green color."""
        svg = _generate_badge_svg("status", "up")
        self.assertIn("<svg", svg)
        self.assertIn("#4c1", svg)  # green color
        self.assertIn("UP", svg)  # uppercase state text
        self.assertIn("status", svg)  # label

    def test_generate_badge_down_state(self):
        """Badge with 'down' state should have red color."""
        svg = _generate_badge_svg("status", "down")
        self.assertIn("#e05d44", svg)  # red color
        self.assertIn("DOWN", svg)

    def test_generate_badge_degraded_state(self):
        """Badge with 'degraded' state should have yellow color."""
        svg = _generate_badge_svg("status", "degraded")
        self.assertIn("#dfb317", svg)  # yellow color
        self.assertIn("DEGRADED", svg)

    def test_generate_badge_unknown_state(self):
        """Badge with 'unknown' state should have gray color."""
        svg = _generate_badge_svg("status", "unknown")
        self.assertIn("#9f9f9f", svg)  # gray color
        self.assertIn("UNKNOWN", svg)

    def test_generate_badge_custom_label(self):
        """Badge should use custom label."""
        svg = _generate_badge_svg("API_PROD", "up")
        self.assertIn("API_PROD", svg)

    def test_generate_badge_is_valid_svg(self):
        """Generated badge should be valid SVG XML."""
        svg = _generate_badge_svg("status", "up")
        # Should parse without error
        root = ElementTree.fromstring(svg)
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")

    def test_generate_badge_case_insensitive_state(self):
        """State matching should be case insensitive."""
        svg_lower = _generate_badge_svg("status", "up")
        svg_upper = _generate_badge_svg("status", "UP")
        svg_mixed = _generate_badge_svg("status", "Up")
        # All should have the same green color
        self.assertIn("#4c1", svg_lower)
        self.assertIn("#4c1", svg_upper)
        self.assertIn("#4c1", svg_mixed)

    def test_generate_badge_unknown_state_fallback(self):
        """Unknown state values should fallback to gray."""
        svg = _generate_badge_svg("status", "invalid_state")
        self.assertIn("#9f9f9f", svg)  # gray color

    def test_generate_badge_style_flat(self):
        """Badge with flat style should not have gradient."""
        svg = _generate_badge_svg("status", "up", style="flat")
        self.assertIn("<svg", svg)
        self.assertNotIn("linearGradient", svg)
        self.assertIn("#4c1", svg)

    def test_generate_badge_style_default(self):
        """Badge with default style should have gradient."""
        svg = _generate_badge_svg("status", "up", style="default")
        self.assertIn("linearGradient", svg)

    def test_generate_badge_with_icon(self):
        """Badge should include status icon."""
        svg = _generate_badge_svg("status", "up")
        # Should have circle icon element
        self.assertIn("<circle", svg)

    def test_generate_badge_has_accessibility_attributes(self):
        """Badge should have ARIA role and label for accessibility."""
        svg = _generate_badge_svg("status", "up")
        self.assertIn('role="img"', svg)
        self.assertIn("aria-label=", svg)
        self.assertIn("<title>", svg)


class TestBadgeEndpoint(unittest.TestCase):
    """Integration tests for /badge.svg endpoint.

    Each test uses its own fresh database to avoid state pollution.
    """

    def _clear_cache(self):
        """Clear the status cache directly."""
        _status_cache._cached_result = None
        _status_cache._revalidating = False

    def setUp(self):
        """Set up test server with fresh database for each test."""
        self._clear_cache()

        self.db_file = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.db_file.close()
        self.db_conn = init_db(self.db_file.name)

        handler_class = _create_handler_class(self.db_conn)
        self.server = HTTPServer(("127.0.0.1", 0), handler_class)
        self.port = self.server.server_address[1]
        self.base_url = f"http://127.0.0.1:{self.port}"

        self.server_thread = Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

    def tearDown(self):
        """Tear down test server."""
        self.server.shutdown()
        self._clear_cache()
        time.sleep(0.05)  # Allow background threads to complete
        self.db_conn.close()
        os.unlink(self.db_file.name)

    def _add_check(self, url_name: str, url: str, is_up: bool):
        """Helper to add a check record."""
        self._clear_cache()  # Clear before insert
        check = CheckResult(
            url_name=url_name,
            url=url,
            checked_at=datetime.now(UTC),
            is_up=is_up,
            status_code=200 if is_up else 500,
            response_time_ms=100 if is_up else 0,
            error_message=None if is_up else "Connection failed",
        )
        insert_check(self.db_conn, check)
        self._clear_cache()  # Clear after insert

    def test_badge_endpoint_returns_svg(self):
        """GET /badge.svg should return SVG content type."""
        req = Request(f"{self.base_url}/badge.svg")
        with urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("image/svg+xml", resp.headers["Content-Type"])

    def test_badge_endpoint_returns_valid_svg(self):
        """GET /badge.svg should return valid SVG XML."""
        req = Request(f"{self.base_url}/badge.svg")
        with urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8")
            # Should parse without error
            root = ElementTree.fromstring(content)
            self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")

    def test_badge_endpoint_unknown_when_no_services(self):
        """Badge should show 'unknown' when no services configured."""
        # Fresh DB, no data added, cache cleared
        self._clear_cache()
        req = Request(f"{self.base_url}/badge.svg")
        with urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8")
            self.assertIn("UNKNOWN", content)
            self.assertIn("#9f9f9f", content)  # gray

    def test_badge_endpoint_up_when_all_services_up(self):
        """Badge should show 'up' when all services are up."""
        self._add_check("API", "https://api.example.com", is_up=True)
        self._add_check("WEB", "https://web.example.com", is_up=True)
        self._clear_cache()

        req = Request(f"{self.base_url}/badge.svg")
        with urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8")
            self.assertIn("UP", content)
            self.assertIn("#4c1", content)  # green

    def test_badge_endpoint_down_when_all_services_down(self):
        """Badge should show 'down' when all services are down."""
        self._add_check("API", "https://api.example.com", is_up=False)
        self._add_check("WEB", "https://web.example.com", is_up=False)
        self._clear_cache()

        req = Request(f"{self.base_url}/badge.svg")
        with urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8")
            self.assertIn("DOWN", content)
            self.assertIn("#e05d44", content)  # red

    def test_badge_endpoint_degraded_when_some_services_down(self):
        """Badge should show 'degraded' when some services are down."""
        self._add_check("API", "https://api.example.com", is_up=True)
        self._add_check("WEB", "https://web.example.com", is_up=False)
        self._clear_cache()

        req = Request(f"{self.base_url}/badge.svg")
        with urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8")
            self.assertIn("DEGRADED", content)
            self.assertIn("#dfb317", content)  # yellow

    def test_badge_endpoint_specific_service_up(self):
        """Badge for specific service should show correct status."""
        self._add_check("API", "https://api.example.com", is_up=True)
        self._clear_cache()

        req = Request(f"{self.base_url}/badge.svg?url=API")
        with urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8")
            self.assertIn("API", content)  # service name as label
            self.assertIn("UP", content)
            self.assertIn("#4c1", content)  # green

    def test_badge_endpoint_specific_service_down(self):
        """Badge for specific down service should show red."""
        self._add_check("API", "https://api.example.com", is_up=False)
        self._clear_cache()

        req = Request(f"{self.base_url}/badge.svg?url=API")
        with urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8")
            self.assertIn("API", content)
            self.assertIn("DOWN", content)
            self.assertIn("#e05d44", content)  # red

    def test_badge_endpoint_service_not_found(self):
        """Badge for non-existent service should return 404."""
        req = Request(f"{self.base_url}/badge.svg?url=NONEXIST")
        try:
            with urlopen(req, timeout=5):
                self.fail("Expected 404 error")
        except Exception as e:
            self.assertIn("404", str(e))

    def test_badge_endpoint_invalid_url_name(self):
        """Badge with invalid URL name should return 400."""
        req = Request(f"{self.base_url}/badge.svg?url=../etc/passwd")
        try:
            with urlopen(req, timeout=5):
                self.fail("Expected 400 error")
        except Exception as e:
            self.assertIn("400", str(e))

    def test_badge_endpoint_style_flat(self):
        """Badge with style=flat should return flat badge."""
        self._add_check("API", "https://api.example.com", is_up=True)
        self._clear_cache()

        req = Request(f"{self.base_url}/badge.svg?style=flat")
        with urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8")
            self.assertNotIn("linearGradient", content)

    def test_badge_endpoint_style_and_url(self):
        """Badge with both style and url params should work."""
        self._add_check("API", "https://api.example.com", is_up=True)
        self._clear_cache()

        req = Request(f"{self.base_url}/badge.svg?url=API&style=flat")
        with urlopen(req, timeout=5) as resp:
            content = resp.read().decode("utf-8")
            self.assertIn("API", content)
            self.assertNotIn("linearGradient", content)

    def test_badge_endpoint_caching_headers(self):
        """Badge should have appropriate caching headers."""
        req = Request(f"{self.base_url}/badge.svg")
        with urlopen(req, timeout=5) as resp:
            self.assertIn("max-age", resp.headers.get("Cache-Control", ""))


if __name__ == "__main__":
    unittest.main()
