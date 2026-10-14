"""SSRF-safe website fetching and HTML normalization service.

Uses HTTPX and BeautifulSoup4 to fetch public webpages, enforce SSRF protections,
harden against DNS rebinding, handle timeouts, reject oversized/non-HTML payloads,
and clean text content.
"""

import ipaddress
import logging
import socket
import ssl
import urllib.parse
from typing import Callable, Optional, Tuple, Union
import httpcore
from httpcore._backends.auto import AutoBackend
from bs4 import BeautifulSoup
import httpx

logger = logging.getLogger("changeradar.scraper")

# Safety and size limits
MAX_RESPONSE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_REDIRECTS = 5
DEFAULT_TIMEOUT = 12.0

DEFAULT_HEADERS = {
    "User-Agent": "ChangeRadar/0.1 (Webpage Content Sentinel; College SGP MVP)",
    "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9,*/*;q=0.8",
}

# Known internal and cloud metadata hostnames
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "instance-data",
}


class SecuritySSRFError(httpcore.ConnectError):
    """Raised when an outbound connection attempt targets a forbidden or unsafe IP/host."""
    pass


def is_ip_safe(ip_obj: Union[ipaddress.IPv4Address, ipaddress.IPv6Address]) -> Tuple[bool, str]:
    """Validate whether an IP address is a safe, globally reachable public destination.

    Rejects loopback, private, link-local, reserved, multicast, unspecified, and non-global IPs.
    Also unpacks and validates IPv4-mapped IPv6 addresses.
    """
    if ip_obj.is_loopback:
        return False, f"Resolved loopback address '{ip_obj}' is blocked (SSRF prevention)."
    if ip_obj.is_private:
        return False, f"Resolved private network address '{ip_obj}' is blocked (SSRF prevention)."
    if ip_obj.is_link_local:
        return False, f"Resolved link-local address '{ip_obj}' is blocked (SSRF prevention)."
    if ip_obj.is_reserved:
        return False, f"Resolved reserved address '{ip_obj}' is blocked (SSRF prevention)."
    if ip_obj.is_multicast:
        return False, f"Resolved multicast address '{ip_obj}' is blocked (SSRF prevention)."
    if ip_obj.is_unspecified:
        return False, f"Resolved unspecified address '{ip_obj}' is blocked (SSRF prevention)."
    if not ip_obj.is_global and not ip_obj.is_multicast:
        return False, f"Resolved non-global address '{ip_obj}' is blocked (SSRF prevention)."

    # Handle IPv4-mapped IPv6 addresses (e.g., ::ffff:127.0.0.1)
    if getattr(ip_obj, "ipv4_mapped", None):
        mapped = ip_obj.ipv4_mapped
        safe, reason = is_ip_safe(mapped)
        if not safe:
            return False, reason

    return True, ""


def resolve_and_validate_host(
    host: str,
    port: int = 80,
    dns_resolver: Optional[Callable] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Resolve hostname and validate ALL associated DNS IP records against SSRF rules.

    Guarantees:
    - Fails closed if host is empty, blocked, or fails DNS resolution.
    - If host is already an IP literal, validates it directly.
    - If ANY resolved IP in the DNS answer is unsafe (including mixed public/private answers),
      fails closed and rejects the entire answer.
    - Returns (safe_ip_literal, None) on success, or (None, error_reason) on failure.
    """
    if not host or not host.strip():
        return None, "URL does not contain a valid hostname."

    hostname_lower = host.lower().strip(".")

    # Block obvious local hostnames
    if hostname_lower in BLOCKED_HOSTNAMES or hostname_lower.endswith(".local"):
        return None, f"Access to '{host}' is blocked for security (SSRF prevention)."

    # 1. Check if host is already an IP literal
    try:
        ip_direct = ipaddress.ip_address(hostname_lower)
        safe, reason = is_ip_safe(ip_direct)
        if not safe:
            return None, reason
        return str(ip_direct), None
    except ValueError:
        pass  # Host is a domain name, proceed to DNS resolution

    # 2. Resolve hostname to all associated IP addresses
    resolver_fn = dns_resolver or (
        lambda h, p: socket.getaddrinfo(h, p, socket.AF_UNSPEC, socket.SOCK_STREAM)
    )

    try:
        addr_info = resolver_fn(hostname_lower, port)
    except socket.gaierror as exc:
        return None, f"DNS resolution failed for '{host}': {str(exc)}"
    except Exception as exc:
        return None, f"Error resolving hostname '{host}': {str(exc)}"

    if not addr_info:
        return None, f"No IP addresses resolved for hostname '{host}'."

    # 3. Validate EVERY resolved IP address. If ANY is unsafe, fail closed!
    for item in addr_info:
        ip_str = item[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return None, f"Resolved invalid IP address: '{ip_str}'."

        safe, reason = is_ip_safe(ip_obj)
        if not safe:
            return None, f"DNS answer for '{host}' contained blocked address '{ip_str}': {reason}"

    # All resolved IPs are safe. Pick the first resolved IP for the pinned connection.
    chosen_ip = addr_info[0][4][0]
    return chosen_ip, None


def is_safe_url(url: str, dns_resolver: Optional[Callable] = None) -> Tuple[bool, str]:
    """Validate URL protocol and inspect resolved IP addresses to block SSRF attacks.

    Rejects loopback, private, link-local, reserved, multicast, or internal addresses.
    """
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception as exc:
        return False, f"Invalid URL syntax: {str(exc)}"

    if parsed.scheme.lower() not in {"http", "https"}:
        return False, f"Unsupported URL scheme '{parsed.scheme}'. Only HTTP and HTTPS are allowed."

    hostname = parsed.hostname
    if not hostname:
        return False, "URL does not contain a valid hostname."

    default_port = 443 if parsed.scheme.lower() == "https" else 80
    port = parsed.port or default_port

    safe_ip, err = resolve_and_validate_host(hostname, port, dns_resolver=dns_resolver)
    if err:
        return False, err

    return True, ""


class SSRFSafeBackend(AutoBackend):
    """Network backend that resolves DNS at connection time and pins the connection to the validated IP."""

    def __init__(self, dns_resolver: Optional[Callable] = None):
        super().__init__()
        self.dns_resolver = dns_resolver

    async def connect_tcp(
        self,
        host: str,
        port: int,
        timeout: Optional[float] = None,
        local_address: Optional[str] = None,
        socket_options=None,
    ):
        # Resolve and validate host at the exact moment of connection
        safe_ip, err = resolve_and_validate_host(host, port, dns_resolver=self.dns_resolver)
        if err:
            logger.warning("SSRF connection blocked for %s:%d: %s", host, port, err)
            raise SecuritySSRFError(f"SSRF Security Violation: {err}")

        # Connect directly to the validated IP literal to prevent DNS rebinding
        await self._init_backend()
        return await self._backend.connect_tcp(
            safe_ip,
            port,
            timeout=timeout,
            local_address=local_address,
            socket_options=socket_options,
        )


class SSRFSafeTransport(httpx.AsyncHTTPTransport):
    """Custom HTTPX transport enforcing DNS resolution validation and IP pinning."""

    def __init__(
        self,
        dns_resolver: Optional[Callable] = None,
        verify: Union[ssl.SSLContext, str, bool] = True,
        **kwargs
    ):
        super().__init__(verify=verify, **kwargs)
        self.dns_resolver = dns_resolver

        # Configure connection pool with SSRFSafeBackend and disable keepalive connection reuse
        backend = SSRFSafeBackend(dns_resolver=dns_resolver)
        ssl_ctx = getattr(self._pool, "_ssl_context", None)
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl_ctx,
            network_backend=backend,
            max_connections=10,
            max_keepalive_connections=0,
            keepalive_expiry=0.0,
            retries=0,
        )


def normalize_html_content(raw_html: str, selector: Optional[str] = None) -> Tuple[bool, str, str]:
    """Parse raw HTML with BeautifulSoup, isolate selector, and clean whitespace.

    Returns: (success: bool, clean_text: str, error_message: str)
    """
    try:
        soup = BeautifulSoup(raw_html, "html.parser")

        # Strip noisy dynamic and non-content tags
        for tag in soup(["script", "style", "noscript", "svg", "canvas", "iframe"]):
            tag.decompose()

        if selector:
            target_el = soup.select_one(selector)
            if not target_el:
                return False, "", f"CSS selector '{selector}' did not match any content on the page."
            soup = target_el

        # Extract text and normalize line breaks and spacing
        lines = [line.strip() for line in soup.get_text(separator="\n").splitlines()]
        clean_lines = [line for line in lines if line]
        clean_text = "\n".join(clean_lines)

        return True, clean_text, ""
    except Exception as exc:
        return False, "", f"HTML normalization failed: {str(exc)}"


async def fetch_webpage_content_standard(
    url: str,
    selector: Optional[str] = None,
    transport: Optional[httpx.AsyncHTTPTransport] = None,
    dns_resolver: Optional[Callable] = None,
) -> Tuple[bool, str, str]:
    """Fetch webpage HTML safely using HTTPX with SSRF checks, redirect validation, and timeouts.

    Preserved default scraper implementation for standard webpages.
    Returns: (success: bool, clean_text: str, error_message: str)
    """
    current_url = url
    redirect_count = 0
    safe_transport = transport or SSRFSafeTransport(dns_resolver=dns_resolver)

    try:
        async with httpx.AsyncClient(
            transport=safe_transport,
            headers=DEFAULT_HEADERS,
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=False,
        ) as client:
            while True:
                # 1. Validate destination URL against SSRF
                is_safe, reason = is_safe_url(current_url, dns_resolver=dns_resolver)
                if not is_safe:
                    return False, "", f"SSRF Security Violation: {reason}"

                # 2. Fetch page stream with size checks
                async with client.stream("GET", current_url) as response:
                    # Check for redirects (301, 302, 303, 307, 308)
                    if response.status_code in {301, 302, 303, 307, 308}:
                        redirect_count += 1
                        if redirect_count > MAX_REDIRECTS:
                            return False, "", f"Too many redirects (exceeded limit of {MAX_REDIRECTS})."

                        location = response.headers.get("Location")
                        if not location:
                            return False, "", "Redirect response did not include a Location header."

                        # Re-resolve and revalidate relative or absolute redirect destination
                        current_url = urllib.parse.urljoin(current_url, location)
                        continue

                    # Check HTTP status code
                    if response.status_code >= 400:
                        return False, "", f"HTTP {response.status_code}: {response.reason_phrase}"

                    # Verify Content-Type is textual/HTML
                    content_type = response.headers.get("Content-Type", "").lower()
                    allowed_types = ("text/html", "application/xhtml+xml", "text/plain", "application/xml")
                    if content_type and not any(allowed in content_type for allowed in allowed_types):
                        return False, "", f"Unsupported Content-Type '{content_type}'. Expected HTML or text."

                    # Read payload up to size limit
                    chunks = []
                    downloaded_bytes = 0
                    async for chunk in response.aiter_bytes():
                        downloaded_bytes += len(chunk)
                        if downloaded_bytes > MAX_RESPONSE_SIZE:
                            return False, "", f"Response exceeded maximum allowed size of {MAX_RESPONSE_SIZE // 1024 // 1024}MB."
                        chunks.append(chunk)

                    raw_bytes = b"".join(chunks)
                    # Decode text
                    encoding = response.encoding or "utf-8"
                    try:
                        raw_html = raw_bytes.decode(encoding, errors="replace")
                    except Exception:
                        raw_html = raw_bytes.decode("utf-8", errors="replace")

                    break

        # 3. Normalize HTML and extract clean text
        return normalize_html_content(raw_html, selector)

    except httpx.TimeoutException:
        return False, "", f"Connection timed out after {DEFAULT_TIMEOUT} seconds while contacting {current_url}."
    except (httpx.ConnectError, SecuritySSRFError) as exc:
        err_msg = str(exc)
        if "SSRF Security Violation" in err_msg or "SSRF" in err_msg:
            return False, "", err_msg if "SSRF Security Violation" in err_msg else f"SSRF Security Violation: {err_msg}"
        return False, "", f"Connection failed: Unable to connect to host ({str(exc)})."
    except httpx.HTTPError as exc:
        return False, "", f"HTTP error occurred: {str(exc)}"
    except Exception as exc:
        err_msg = str(exc)
        if "SSRF Security Violation" in err_msg:
            return False, "", err_msg
        return False, "", f"Unexpected fetch error: {str(exc)}"


async def fetch_webpage_content(
    url: str,
    selector: Optional[str] = None,
    render_js: bool = False,
    fallback_to_standard: bool = True,
    dns_resolver: Optional[Callable] = None,
) -> Tuple[bool, str, str]:
    """Fetch webpage content safely, preserving HTTPX as default with optional browser JS rendering.

    - By default (render_js=False): Uses lightweight HTTPX + BeautifulSoup scraper. Does not launch a browser.
    - If render_js=True: Uses Playwright headless Chromium adapter to execute client-side JavaScript.
    - If browser dependencies are unavailable or launch fails:
      - If fallback_to_standard=True: Logs warning and safely falls back to standard HTTP scraper.
      - If fallback_to_standard=False: Returns actionable error message detailing missing dependencies.
    """
    if not render_js:
        return await fetch_webpage_content_standard(url, selector, dns_resolver=dns_resolver)

    # Optional JavaScript rendering via Playwright
    try:
        from .browser_scraper import is_playwright_available, fetch_webpage_content_browser

        available, avail_msg = is_playwright_available()
        if not available:
            if fallback_to_standard:
                logger.warning(
                    "Playwright not available (%s). Safely falling back to standard scraper for '%s'.",
                    avail_msg,
                    url
                )
                return await fetch_webpage_content_standard(url, selector, dns_resolver=dns_resolver)
            return False, "", avail_msg

        success, text, err = await fetch_webpage_content_browser(url, selector)
        if not success and fallback_to_standard and "SSRF" not in err:
            logger.warning(
                "Browser rendering encountered error ('%s'). Falling back to standard scraper for '%s'.",
                err,
                url
            )
            return await fetch_webpage_content_standard(url, selector, dns_resolver=dns_resolver)
        return success, text, err

    except Exception as exc:
        if fallback_to_standard:
            logger.warning(
                "Failed to invoke browser scraper (%s). Falling back to standard scraper for '%s'.",
                exc,
                url
            )
            return await fetch_webpage_content_standard(url, selector, dns_resolver=dns_resolver)
        return False, "", f"Browser rendering adapter error: {str(exc)}"
