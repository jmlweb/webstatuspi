"""Tests for security module."""

import pytest

from webstatuspi.security import (
    SSRFError,
    validate_url_for_ssrf,
    validate_url_name,
)


class TestValidateUrlForSSRF:
    """Tests for SSRF URL validation."""

    def test_allows_http_url(self) -> None:
        """Should allow valid HTTP URLs."""
        # Should not raise
        validate_url_for_ssrf("http://example.com", allow_private=True)

    def test_allows_https_url(self) -> None:
        """Should allow valid HTTPS URLs."""
        validate_url_for_ssrf("https://example.com", allow_private=True)

    def test_blocks_file_scheme(self) -> None:
        """Should block file:// URLs."""
        with pytest.raises(SSRFError, match="Scheme 'file' not allowed"):
            validate_url_for_ssrf("file:///etc/passwd")

    def test_blocks_ftp_scheme(self) -> None:
        """Should block ftp:// URLs."""
        with pytest.raises(SSRFError, match="Scheme 'ftp' not allowed"):
            validate_url_for_ssrf("ftp://example.com/file.txt")

    def test_blocks_gopher_scheme(self) -> None:
        """Should block gopher:// URLs."""
        with pytest.raises(SSRFError, match="Scheme 'gopher' not allowed"):
            validate_url_for_ssrf("gopher://localhost")

    def test_blocks_data_scheme(self) -> None:
        """Should block data: URLs."""
        with pytest.raises(SSRFError, match="Scheme 'data' not allowed"):
            validate_url_for_ssrf("data:text/html,<script>alert(1)</script>")

    def test_blocks_localhost(self) -> None:
        """Should block localhost URLs."""
        with pytest.raises(SSRFError, match="Localhost access not allowed"):
            validate_url_for_ssrf("http://localhost/admin")

    def test_blocks_localhost_127(self) -> None:
        """Should block 127.0.0.1 URLs."""
        with pytest.raises(SSRFError, match="Localhost access not allowed"):
            validate_url_for_ssrf("http://127.0.0.1/")

    def test_blocks_localhost_ipv6(self) -> None:
        """Should block ::1 (IPv6 localhost)."""
        with pytest.raises(SSRFError, match="Localhost access not allowed"):
            validate_url_for_ssrf("http://[::1]/")

    def test_blocks_zero_address(self) -> None:
        """Should block 0.0.0.0 URLs."""
        with pytest.raises(SSRFError, match="Localhost access not allowed"):
            validate_url_for_ssrf("http://0.0.0.0/")

    def test_blocks_ssh_port(self) -> None:
        """Should block port 22 (SSH)."""
        with pytest.raises(SSRFError, match="Port 22 is blocked"):
            validate_url_for_ssrf("http://example.com:22/")

    def test_blocks_mysql_port(self) -> None:
        """Should block port 3306 (MySQL)."""
        with pytest.raises(SSRFError, match="Port 3306 is blocked"):
            validate_url_for_ssrf("http://example.com:3306/")

    def test_blocks_postgres_port(self) -> None:
        """Should block port 5432 (PostgreSQL)."""
        with pytest.raises(SSRFError, match="Port 5432 is blocked"):
            validate_url_for_ssrf("http://example.com:5432/")

    def test_blocks_redis_port(self) -> None:
        """Should block port 6379 (Redis)."""
        with pytest.raises(SSRFError, match="Port 6379 is blocked"):
            validate_url_for_ssrf("http://example.com:6379/")

    def test_blocks_empty_hostname(self) -> None:
        """Should block URLs without hostname."""
        with pytest.raises(SSRFError, match="No hostname"):
            validate_url_for_ssrf("http:///path")

    def test_blocks_invalid_url(self) -> None:
        """Should block invalid URLs."""
        with pytest.raises(SSRFError):
            validate_url_for_ssrf("not-a-valid-url")

    def test_allows_standard_ports(self) -> None:
        """Should allow standard HTTP/HTTPS ports."""
        validate_url_for_ssrf("http://example.com:80/", allow_private=True)
        validate_url_for_ssrf("https://example.com:443/", allow_private=True)

    def test_allows_high_ports(self) -> None:
        """Should allow high ports like 8080."""
        validate_url_for_ssrf("http://example.com:8080/", allow_private=True)

    def test_allow_private_flag_skips_ip_check(self) -> None:
        """allow_private=True should skip private IP validation."""
        # These would normally be blocked
        validate_url_for_ssrf("http://192.168.1.1/", allow_private=True)
        validate_url_for_ssrf("http://10.0.0.1/", allow_private=True)

    def test_blocks_private_10_range(self) -> None:
        """Should block 10.x.x.x private range."""
        with pytest.raises(SSRFError, match="Private IP address not allowed"):
            validate_url_for_ssrf("http://10.0.0.1/")

    def test_blocks_private_172_range(self) -> None:
        """Should block 172.16.x.x private range."""
        with pytest.raises(SSRFError, match="Private IP address not allowed"):
            validate_url_for_ssrf("http://172.16.0.1/")

    def test_blocks_private_192_range(self) -> None:
        """Should block 192.168.x.x private range."""
        with pytest.raises(SSRFError, match="Private IP address not allowed"):
            validate_url_for_ssrf("http://192.168.1.1/")

    def test_blocks_cloud_metadata_aws(self) -> None:
        """Should block AWS metadata endpoint."""
        with pytest.raises(SSRFError, match="Private IP address not allowed"):
            validate_url_for_ssrf("http://169.254.169.254/latest/meta-data/")


class TestValidateUrlName:
    """Tests for URL name validation."""

    def test_allows_alphanumeric(self) -> None:
        """Should allow alphanumeric names."""
        assert validate_url_name("test123") == "test123"

    def test_allows_underscores(self) -> None:
        """Should allow underscores."""
        assert validate_url_name("my_url") == "my_url"

    def test_allows_hyphens(self) -> None:
        """Should allow hyphens."""
        assert validate_url_name("my-url") == "my-url"

    def test_allows_max_10_chars(self) -> None:
        """Should allow exactly 10 characters."""
        assert validate_url_name("abcdefghij") == "abcdefghij"

    def test_rejects_11_chars(self) -> None:
        """Should reject names longer than 10 characters."""
        assert validate_url_name("abcdefghijk") is None

    def test_rejects_empty(self) -> None:
        """Should reject empty names."""
        assert validate_url_name("") is None

    def test_rejects_none(self) -> None:
        """Should reject None."""
        assert validate_url_name(None) is None

    def test_rejects_path_traversal_dots(self) -> None:
        """Should reject path traversal sequences."""
        assert validate_url_name("../etc") is None
        assert validate_url_name("..") is None

    def test_rejects_forward_slash(self) -> None:
        """Should reject forward slashes."""
        assert validate_url_name("a/b") is None

    def test_rejects_backslash(self) -> None:
        """Should reject backslashes."""
        assert validate_url_name("a\\b") is None

    def test_rejects_null_byte(self) -> None:
        """Should reject null bytes."""
        assert validate_url_name("test\x00end") is None

    def test_rejects_control_chars(self) -> None:
        """Should reject control characters."""
        assert validate_url_name("test\x01end") is None

    def test_rejects_spaces(self) -> None:
        """Should reject spaces."""
        assert validate_url_name("a b") is None

    def test_rejects_special_chars(self) -> None:
        """Should reject special characters like @ # $ %."""
        assert validate_url_name("test@") is None
        assert validate_url_name("test#") is None
        assert validate_url_name("test$") is None
        assert validate_url_name("test%") is None
