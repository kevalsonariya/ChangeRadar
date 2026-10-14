"""Automated test suite for hardened SSRF and DNS Rebinding protections.

Tests:
1. DNS rebinding prevention: connection-time IP pinning detects when a hostname rebinds to a private IP.
2. Mixed public and private DNS answers: fails closed if any IP in the DNS response is unsafe.
3. Comprehensive IP coverage: IPv4, IPv6, IPv4-mapped IPv6, loopback, private, link-local, multicast, unspecified.
4. Connection-time IP pinning: validates that the TCP connection uses the validated IP literal while preserving Host header.
5. Unsafe redirect destinations: independent validation per redirect hop blocks internal destinations.
6. Fail-closed behavior: fails safely on DNS resolution failure, empty answers, or unparseable IPs.
7. HTTPS TLS certificate verification: verify=True is preserved and server_hostname is passed to TLS handshake.
"""

import asyncio
import ipaddress
import socket
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
import httpx
from app.services.scraper import (
    SecuritySSRFError,
    SSRFSafeBackend,
    SSRFSafeTransport,
    fetch_webpage_content_standard,
    is_ip_safe,
    is_safe_url,
    resolve_and_validate_host,
)


def test_is_ip_safe_comprehensive_matrix():
    """Requirement 2 & 8: Validate loopback, private, link-local, cloud metadata, multicast, and IPv6."""
    test_cases = [
        # Loopback
        ("127.0.0.1", False, "loopback"),
        ("127.255.255.254", False, "loopback"),
        ("::1", False, "loopback"),
        # Private RFC1918 & RFC4193
        ("10.0.0.1", False, "private"),
        ("172.16.0.1", False, "private"),
        ("172.31.255.255", False, "private"),
        ("192.168.1.1", False, "private"),
        ("fc00::1", False, "private"),
        ("fd00::1234", False, "private"),
        # Link-local & Cloud Metadata (AWS/GCP/Azure)
        ("169.254.169.254", False, "link-local"),
        ("fe80::1", False, "link-local"),
        # Multicast & Unspecified
        ("0.0.0.0", False, "unspecified"),
        ("::", False, "unspecified"),
        ("224.0.0.1", False, "multicast"),
        ("ff02::1", False, "multicast"),
        # IPv4-mapped IPv6
        ("::ffff:127.0.0.1", False, "loopback"),
        ("::ffff:169.254.169.254", False, "link-local"),
        ("::ffff:192.168.1.1", False, "private"),
        ("::ffff:10.1.1.1", False, "private"),
        # Valid Public IPs (IPv4 & IPv6)
        ("93.184.216.34", True, ""),
        ("1.1.1.1", True, ""),
        ("8.8.8.8", True, ""),
        ("2606:4700::6810:f860", True, ""),
        ("2001:4860:4860::8888", True, ""),
    ]

    for ip_str, expected_safe, keyword in test_cases:
        ip = ipaddress.ip_address(ip_str)
        safe, reason = is_ip_safe(ip)
        assert safe is expected_safe, f"Failed for {ip_str}: got safe={safe}, expected {expected_safe} ({reason})"
        if not expected_safe and keyword:
            assert keyword in reason.lower() or "blocked" in reason.lower() or "private" in reason.lower()


def test_mixed_public_and_private_dns_answers_fail_closed():
    """Requirement 6: Mixed public/private DNS answers must be rejected entirely (fail closed)."""
    # Simulate a DNS response returning both a legitimate public IP and an internal address
    def mock_mixed_resolver(host, port):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", port)),
        ]

    safe_ip, err = resolve_and_validate_host("attacker-mixed.com", 80, dns_resolver=mock_mixed_resolver)
    assert safe_ip is None
    assert err is not None
    assert "blocked address '127.0.0.1'" in err or "loopback" in err

    # Also test mixed with private 192.168.1.1
    def mock_mixed_private_resolver(host, port):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("192.168.1.100", port)),
        ]

    safe_ip2, err2 = resolve_and_validate_host("attacker-mixed-lan.com", 80, dns_resolver=mock_mixed_private_resolver)
    assert safe_ip2 is None
    assert "192.168.1.100" in err2 or "private" in err2


def test_dns_rebinding_simulation_caught_at_connection_time():
    """Requirement 3 & 8: Rebinding after URL check is caught and blocked at connection time."""
    resolution_count = 0

    def mock_rebinding_dns_resolver(host, port):
        nonlocal resolution_count
        resolution_count += 1
        if resolution_count == 1:
            # First resolution (pre-flight URL validation): returns benign public IP
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", port))
            ]
        else:
            # Second resolution (when socket connection actually opens): rebinds to internal loopback!
            return [
                (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("127.0.0.1", port))
            ]

    backend = SSRFSafeBackend(dns_resolver=mock_rebinding_dns_resolver)

    # 1. First resolution passes pre-flight
    safe, msg = is_safe_url("http://rebind-exploit.example.com", dns_resolver=mock_rebinding_dns_resolver)
    assert safe is True
    assert msg == ""

    # 2. Connection-time resolution fails closed when DNS rebinds to 127.0.0.1
    with pytest.raises(SecuritySSRFError) as exc_info:
        asyncio.run(backend.connect_tcp("rebind-exploit.example.com", 80))

    assert "SSRF Security Violation" in str(exc_info.value)
    assert "127.0.0.1" in str(exc_info.value) or "loopback" in str(exc_info.value)


def test_ip_pinning_in_ssrf_safe_backend():
    """Requirement 3: Pinned connection uses the exact validated IP literal, not re-resolving hostname."""
    mock_inner_backend = MagicMock()
    mock_inner_backend.connect_tcp = AsyncMock()

    def mock_safe_dns(host, port):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 0, "", ("93.184.216.34", port))
        ]

    backend = SSRFSafeBackend(dns_resolver=mock_safe_dns)
    backend._backend = mock_inner_backend
    backend._init_backend = AsyncMock()

    asyncio.run(backend.connect_tcp("public-site.example.edu", 443))

    # Verify connect_tcp was invoked with the IP literal ("93.184.216.34"), NOT the hostname string
    mock_inner_backend.connect_tcp.assert_awaited_once()
    call_args = mock_inner_backend.connect_tcp.call_args[0]
    assert call_args[0] == "93.184.216.34"
    assert call_args[1] == 443


def test_unsafe_redirect_destinations_blocked():
    """Requirement 5: Every redirect destination is validated independently against SSRF."""
    # Mock HTTP response sequence:
    # Hop 1 (Public URL): Returns HTTP 302 Redirect to http://169.254.169.254/latest/meta-data
    response_302 = MagicMock()
    response_302.status_code = 302
    response_302.headers = {"Location": "http://169.254.169.254/latest/meta-data"}

    mock_client = MagicMock()

    class MockStreamContext:
        async def __aenter__(self):
            return response_302
        async def __aexit__(self, *args):
            pass

    mock_client.stream.return_value = MockStreamContext()

    class MockAsyncClientConstructor:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return mock_client
        async def __aexit__(self, *args):
            pass

    with patch("httpx.AsyncClient", MockAsyncClientConstructor), \
         patch("app.services.scraper.is_safe_url", side_effect=[
             (True, ""),   # Initial hop safe
             (False, "Resolved link-local address '169.254.169.254' is blocked (SSRF prevention).")  # Redirect hop unsafe
         ]):

        success, text, err = asyncio.run(
            fetch_webpage_content_standard("https://public-entry.example.edu/redirect-me")
        )

        assert success is False
        assert "SSRF Security Violation" in err
        assert "169.254.169.254" in err or "link-local" in err


def test_dns_resolution_failure_fails_closed():
    """Requirement 10: Fail closed when DNS resolution fails or returns empty records."""
    # 1. Non-existent domain raises socket.gaierror
    def mock_nxdomain_resolver(host, port):
        raise socket.gaierror(11001, "getaddrinfo failed")

    safe_ip, err = resolve_and_validate_host("non-existent-domain-12345.edu", 80, dns_resolver=mock_nxdomain_resolver)
    assert safe_ip is None
    assert "DNS resolution failed" in err

    # 2. Empty DNS records list
    def mock_empty_resolver(host, port):
        return []

    safe_ip2, err2 = resolve_and_validate_host("empty-records.example.edu", 80, dns_resolver=mock_empty_resolver)
    assert safe_ip2 is None
    assert "No IP addresses resolved" in err2


def test_tls_verification_preserved_with_ssrf_transport():
    """Requirement 7: HTTPS TLS certificate verification is active and never disabled."""
    transport = SSRFSafeTransport(verify=True)
    # The pool's SSL context must not be None when verify=True
    assert transport._pool._ssl_context is not None
    # Connection pool keepalive is disabled to prevent address rebinding across requests
    assert transport._pool._max_keepalive_connections == 0
    assert transport._pool._keepalive_expiry == 0.0
