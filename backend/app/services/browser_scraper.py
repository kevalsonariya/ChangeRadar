"""Headless browser rendering adapter using Playwright with SSRF interception.

Provides optional client-side JavaScript execution for dynamic pages and SPAs,
while strictly enforcing SSRF protections, navigation timeouts, resource limits,
and guaranteed browser context cleanup.
"""

import logging
from typing import Optional, Tuple
from .scraper import is_safe_url, normalize_html_content, DEFAULT_HEADERS, MAX_RESPONSE_SIZE

logger = logging.getLogger("changeradar.browser_scraper")

DEFAULT_BROWSER_TIMEOUT_MS = 15000  # 15 seconds
DEFAULT_SELECTOR_WAIT_MS = 5000     # 5 seconds
DEFAULT_JS_SETTLE_MS = 800          # Settle time for dynamic JS mutations

# Chromium sandbox and resource optimization flags
BROWSER_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-sync",
    "--no-first-run",
    "--mute-audio",
]


def is_playwright_available() -> Tuple[bool, str]:
    """Check if Playwright Python library is installed and importable."""
    try:
        import playwright.async_api  # noqa: F401
        return True, ""
    except ImportError as exc:
        return False, (
            "Playwright is not installed. To enable JavaScript rendering support, "
            "install it via 'pip install playwright' and execute 'playwright install chromium'."
        )


async def fetch_webpage_content_browser(
    url: str,
    selector: Optional[str] = None,
    timeout_ms: int = DEFAULT_BROWSER_TIMEOUT_MS,
) -> Tuple[bool, str, str]:
    """Render and fetch dynamic webpage content using headless Chromium.

    Enforces:
    - Pre-navigation and post-navigation SSRF checks
    - In-flight request interception to block SSRF on redirects and subresources
    - Resource pruning (aborts media, audio, font, and websocket requests)
    - Strict navigation and selector timeouts
    - Guaranteed browser, context, and page closure

    Returns: (success: bool, clean_text: str, error_message: str)
    """
    # 1. Initial SSRF check on target URL
    is_safe, reason = is_safe_url(url)
    if not is_safe:
        return False, "", f"SSRF Security Violation: {reason}"

    # 2. Check Playwright availability
    available, avail_msg = is_playwright_available()
    if not available:
        return False, "", avail_msg

    from playwright.async_api import (
        async_playwright,
        TimeoutError as PlaywrightTimeoutError,
        Error as PlaywrightError,
    )

    playwright_instance = None
    browser = None
    context = None
    page = None

    try:
        playwright_instance = await async_playwright().start()

        # Launch Chromium with headless resource constraints
        try:
            browser = await playwright_instance.chromium.launch(
                headless=True,
                args=BROWSER_LAUNCH_ARGS,
            )
        except Exception as exc:
            err_str = str(exc)
            if "Executable doesn't exist" in err_str or "playwright install" in err_str:
                return False, "", (
                    "Chromium browser executable not found. "
                    "Run 'playwright install chromium' to complete browser setup."
                )
            return False, "", f"Failed to launch browser: {err_str}"

        # Create isolated browser context
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=DEFAULT_HEADERS.get("User-Agent"),
            java_script_enabled=True,
            bypass_csp=False,
            ignore_https_errors=False,
        )
        context.set_default_timeout(timeout_ms)

        ssrf_violation = []

        # 3. Intercept ALL network requests (including subresources and XHR/fetch) to enforce SSRF rules
        async def intercept_request(route):
            req = route.request
            req_url = req.url

            # Block non-HTTP protocols (e.g., file://, gopher://, internal schemes)
            if not req_url.startswith(("http://", "https://")):
                await route.abort("blockedbyclient")
                return

            # Block heavy non-essential subresources to save RAM/CPU
            if req.resource_type in ("media", "font", "websocket"):
                await route.abort("blockedbyclient")
                return

            # Enforce SSRF rules on destination IP
            req_safe, req_reason = is_safe_url(req_url)
            if not req_safe:
                logger.warning("SSRF blocked subresource/redirect request: %s (%s)", req_url, req_reason)
                ssrf_violation.append(f"Blocked request to '{req_url}': {req_reason}")
                await route.abort("blockedbyclient")
                return

            await route.continue_()

        await context.route("**/*", intercept_request)

        # 4. Open page and navigate
        page = await context.new_page()

        try:
            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )
        except PlaywrightTimeoutError:
            return False, "", f"Browser navigation timed out after {timeout_ms / 1000:.1f}s while loading '{url}'."
        except PlaywrightError as exc:
            if ssrf_violation:
                return False, "", f"SSRF Security Violation: {ssrf_violation[0]}"
            return False, "", f"Browser navigation error: {str(exc)}"

        if ssrf_violation:
            return False, "", f"SSRF Security Violation: {ssrf_violation[0]}"

        # 5. Validate final resolved URL against SSRF
        final_url = page.url
        final_safe, final_reason = is_safe_url(final_url)
        if not final_safe:
            return False, "", f"SSRF Security Violation on final URL: {final_reason}"

        # 6. Check response status code if available
        if response and response.status >= 400:
            return False, "", f"HTTP {response.status}: {response.status_text}"

        # 7. Wait for selector if provided, or allow JS settle time
        if selector:
            try:
                await page.wait_for_selector(selector, timeout=DEFAULT_SELECTOR_WAIT_MS, state="attached")
            except PlaywrightTimeoutError:
                # Selector wasn't found within wait period; will be reported during normalization
                pass
        else:
            # Brief settle period for client-side hydration/rendering
            try:
                await page.wait_for_timeout(DEFAULT_JS_SETTLE_MS)
            except Exception:
                pass

        # 8. Extract rendered HTML DOM
        rendered_html = await page.content()

        # Check payload size limit
        if len(rendered_html.encode("utf-8")) > MAX_RESPONSE_SIZE:
            return False, "", f"Rendered HTML exceeded size limit of {MAX_RESPONSE_SIZE // (1024 * 1024)}MB."

        # 9. Normalize content and extract clean text without scripts or volatile tags
        return normalize_html_content(rendered_html, selector)

    except Exception as exc:
        logger.error("Unexpected browser rendering error on %s: %s", url, exc, exc_info=True)
        return False, "", f"Browser rendering failed: {str(exc)}"

    finally:
        # Guaranteed cleanup of all browser resources
        if page:
            try:
                await page.close()
            except Exception:
                pass
        if context:
            try:
                await context.close()
            except Exception:
                pass
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        if playwright_instance:
            try:
                await playwright_instance.stop()
            except Exception:
                pass
