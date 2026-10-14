"""SSRF-safe website fetching and HTML normalization service.

Uses HTTPX and BeautifulSoup4 to fetch public webpages, enforce SSRF protections,
handle timeouts, reject oversized/non-HTML payloads, and clean text content.
"""

import ipaddress
import socket
import urllib.parse
from typing import Optional, Tuple
from bs4 import BeautifulSoup
import httpx

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


def is_safe_url(url: str) -> Tuple[bool, str]:
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

    hostname_lower = hostname.lower().strip(".")

    # Block obvious local hostnames
    if hostname_lower in BLOCKED_HOSTNAMES or hostname_lower.endswith(".local"):
        return False, f"Access to '{hostname}' is blocked for security (SSRF prevention)."

    # Resolve hostname to all associated IP addresses
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        return False, f"DNS resolution failed for '{hostname}': {str(exc)}"
    except Exception as exc:
        return False, f"Error resolving hostname '{hostname}': {str(exc)}"

    if not addr_info:
        return False, f"No IP addresses resolved for hostname '{hostname}'."

    for item in addr_info:
        ip_str = item[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, f"Resolved invalid IP address: '{ip_str}'."

        if ip_obj.is_loopback:
            return False, f"Resolved loopback address '{ip_str}' is blocked (SSRF prevention)."
        if ip_obj.is_private:
            return False, f"Resolved private network address '{ip_str}' is blocked (SSRF prevention)."
        if ip_obj.is_link_local:
            return False, f"Resolved link-local address '{ip_str}' is blocked (SSRF prevention)."
        if ip_obj.is_reserved:
            return False, f"Resolved reserved address '{ip_str}' is blocked (SSRF prevention)."
        if ip_obj.is_multicast:
            return False, f"Resolved multicast address '{ip_str}' is blocked (SSRF prevention)."
        if ip_obj.is_unspecified:
            return False, f"Resolved unspecified address '{ip_str}' is blocked (SSRF prevention)."

    return True, ""


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


async def fetch_webpage_content(
    url: str,
    selector: Optional[str] = None
) -> Tuple[bool, str, str]:
    """Fetch webpage HTML safely using HTTPX with SSRF checks, redirect validation, and timeouts.

    Returns: (success: bool, clean_text: str, error_message: str)
    """
    current_url = url
    redirect_count = 0

    try:
        async with httpx.AsyncClient(
            headers=DEFAULT_HEADERS,
            timeout=DEFAULT_TIMEOUT,
            follow_redirects=False,
        ) as client:
            while True:
                # 1. Validate destination URL against SSRF
                is_safe, reason = is_safe_url(current_url)
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
    except httpx.ConnectError as exc:
        return False, "", f"Connection failed: Unable to connect to host ({str(exc)})."
    except httpx.HTTPError as exc:
        return False, "", f"HTTP error occurred: {str(exc)}"
    except Exception as exc:
        return False, "", f"Unexpected fetch error: {str(exc)}"
