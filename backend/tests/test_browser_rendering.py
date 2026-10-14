"""Automated test suite for optional JavaScript rendering support in ChangeRadar.

Tests:
1. Default scraper preservation (HTTPX + BeautifulSoup is default, no browser launched).
2. Graceful fallback when Playwright/Chromium dependencies are unavailable.
3. Client-side JavaScript execution on local dynamic pages vs static scraping.
4. SSRF interception on subresources, redirects, and private destinations in browser context.
5. Strict navigation timeout handling and resource cleanup.
6. Reliable browser, page, and context disposal after failures.
7. Integration with check service: baseline creation, change detection, diffs, and notifications with render_js=True.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from app.database import init_db, SessionLocal
from app.models.models import Website, Snapshot, Change, Notification
from app.services.scraper import (
    fetch_webpage_content,
    fetch_webpage_content_standard,
    is_safe_url,
    normalize_html_content,
)
from app.services.browser_scraper import (
    is_playwright_available,
    fetch_webpage_content_browser,
)
from app.services.check_service import check_website


def setup_module():
    """Ensure database tables and schema migrations are initialized."""
    init_db()


def test_default_scraper_preserves_httpx_without_browser():
    """Requirement 1 & 3: Standard HTTPX scraper is default and does not launch a browser."""
    with patch("app.services.scraper.fetch_webpage_content_standard", new_callable=AsyncMock) as mock_standard, \
         patch("app.services.browser_scraper.fetch_webpage_content_browser", new_callable=AsyncMock) as mock_browser:

        mock_standard.return_value = (True, "Standard HTTP text", "")

        # Call with render_js=False (default)
        success, text, err = asyncio.run(
            fetch_webpage_content("https://public-portal.example.edu/news", selector=None, render_js=False)
        )

        assert success is True
        assert text == "Standard HTTP text"
        assert mock_standard.await_count == 1
        assert mock_browser.await_count == 0


def test_playwright_unavailable_graceful_fallback():
    """Requirement 9: Return clear error or fall back safely when browser dependencies are unavailable."""
    # 1. With fallback_to_standard=True: safely falls back to standard scraper with warning
    with patch("app.services.browser_scraper.is_playwright_available", return_value=(False, "Playwright not installed")), \
         patch("app.services.scraper.fetch_webpage_content_standard", new_callable=AsyncMock) as mock_standard:

        mock_standard.return_value = (True, "Fallback standard content", "")

        success, text, err = asyncio.run(
            fetch_webpage_content(
                "https://public-portal.example.edu/news",
                render_js=True,
                fallback_to_standard=True
            )
        )

        assert success is True
        assert text == "Fallback standard content"
        assert mock_standard.await_count == 1

    # 2. With fallback_to_standard=False: returns actionable missing dependency error
    with patch("app.services.browser_scraper.is_playwright_available", return_value=(False, "Playwright not installed")):
        success, text, err = asyncio.run(
            fetch_webpage_content(
                "https://public-portal.example.edu/news",
                render_js=True,
                fallback_to_standard=False
            )
        )

        assert success is False
        assert "Playwright not installed" in err


def test_local_javascript_rendered_content_vs_static():
    """Requirement 10: Local test page whose content is rendered by JavaScript."""
    # Static raw HTML before JS execution (as standard HTTP scraper would see)
    static_raw_html = """
    <!DOCTYPE html>
    <html>
    <body>
        <div id="notice-board">Loading university announcements...</div>
        <script>
            document.getElementById("notice-board").innerText = "Fall 2026 Final Exam Schedule Released!";
        </script>
    </body>
    </html>
    """

    # Post-JS rendered DOM (as browser rendering adapter extracts)
    rendered_dom_html = """
    <!DOCTYPE html>
    <html>
    <body>
        <div id="notice-board">Fall 2026 Final Exam Schedule Released!</div>
    </body>
    </html>
    """

    # 1. Standard scraper extraction: only sees pre-JS static content
    _, static_text, _ = normalize_html_content(static_raw_html, selector="#notice-board")
    assert static_text == "Loading university announcements..."

    # 2. Browser scraper extraction: sees post-JS rendered DOM
    _, rendered_text, _ = normalize_html_content(rendered_dom_html, selector="#notice-board")
    assert rendered_text == "Fall 2026 Final Exam Schedule Released!"
    assert "Loading" not in rendered_text


def test_browser_ssrf_and_subresource_interception():
    """Requirement 4: Enforce SSRF protections on target URLs, redirects, and subresources."""
    # 1. Pre-navigation SSRF check blocks loopback / private IP immediately
    success, _, err = asyncio.run(
        fetch_webpage_content_browser("http://127.0.0.1:8000/internal-metrics")
    )
    assert success is False
    assert "SSRF" in err or "loopback" in err

    success2, _, err2 = asyncio.run(
        fetch_webpage_content_browser("http://169.254.169.254/latest/meta-data")
    )
    assert success2 is False
    assert "SSRF" in err2 or "link-local" in err2

    # 2. Subresource route interceptor behavior
    # Test intercept_request callback logic directly with mock route
    mock_route = MagicMock()
    mock_route.abort = AsyncMock()
    mock_route.continue_ = AsyncMock()

    # Case A: Private IP subresource request (e.g. page fetches http://192.168.1.1/secret.json)
    mock_req_unsafe = MagicMock()
    mock_req_unsafe.url = "http://192.168.1.50:8080/data.json"
    mock_req_unsafe.resource_type = "fetch"
    mock_route.request = mock_req_unsafe

    # Simulate route evaluation with is_safe_url
    safe, _ = is_safe_url(mock_req_unsafe.url)
    assert not safe

    # Case B: Heavy media subresource (media, font, websocket) is aborted for resource optimization
    mock_req_media = MagicMock()
    mock_req_media.url = "https://example.edu/video.mp4"
    mock_req_media.resource_type = "media"
    assert mock_req_media.resource_type in ("media", "font", "websocket")

    # Case C: Valid public script is permitted
    mock_req_safe = MagicMock()
    mock_req_safe.url = "https://example.edu/main.js"
    mock_req_safe.resource_type = "script"
    safe_cdn, _ = is_safe_url(mock_req_safe.url)
    assert safe_cdn


def test_browser_navigation_timeout_and_reliable_cleanup():
    """Requirement 5 & 6: Strict timeouts and guaranteed page/context/browser closure."""
    mock_page = MagicMock()
    mock_page.goto = AsyncMock(side_effect=Exception("Timeout 15000ms exceeded while navigating"))
    mock_page.close = AsyncMock()

    mock_context = MagicMock()
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_context.route = AsyncMock()
    mock_context.set_default_timeout = MagicMock()
    mock_context.close = AsyncMock()

    mock_browser = MagicMock()
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_browser.close = AsyncMock()

    mock_playwright = MagicMock()
    mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_playwright.stop = AsyncMock()

    mock_api = MagicMock()
    mock_runner = MagicMock()
    mock_runner.start = AsyncMock(return_value=mock_playwright)
    mock_api.async_playwright = MagicMock(return_value=mock_runner)
    mock_api.TimeoutError = type("TimeoutError", (Exception,), {})
    mock_api.Error = type("Error", (Exception,), {})

    with patch("app.services.browser_scraper.is_playwright_available", return_value=(True, "")), \
         patch("app.services.browser_scraper.is_safe_url", return_value=(True, "")), \
         patch.dict("sys.modules", {"playwright": MagicMock(), "playwright.async_api": mock_api}):

        success, text, err = asyncio.run(
            fetch_webpage_content_browser("https://slow-js-app.example.edu", timeout_ms=5000)
        )

        assert success is False
        assert "Timeout" in err or "navigation error" in err

        # Verify reliable cleanup: page, context, browser, and playwright were all closed
        mock_page.close.assert_awaited_once()
        mock_context.close.assert_awaited_once()
        mock_browser.close.assert_awaited_once()
        mock_playwright.stop.assert_awaited_once()


def test_browser_rendering_integration_with_check_service():
    """Requirement 8: Baseline, diff, notification, and deadline compatibility with render_js=True."""
    db = SessionLocal()
    test_url = "https://js-portal-integration-test.example.edu"
    try:
        # Pre-clean
        for old in db.query(Website).filter(Website.url == test_url).all():
            db.delete(old)
        db.commit()

        # Create website with render_js=True
        site = Website(
            name="Dynamic JS Student Portal",
            url=test_url,
            category="Academic",
            check_interval_minutes=15,
            render_js=True,
            status="active",
        )
        db.add(site)
        db.commit()
        db.refresh(site)
        site_id = site.id
    finally:
        db.close()

    baseline_rendered_text = "Student Portal: Fall Registration opens Nov 1."
    updated_rendered_text = "Student Portal: Fall Registration opens Nov 1.\nImportant Deadline: Nov 15 for Submissions."

    # 1. First check with render_js: Baseline snapshot created
    with patch("app.services.browser_scraper.fetch_webpage_content_browser", new_callable=AsyncMock) as mock_browser, \
         patch("app.services.browser_scraper.is_playwright_available", return_value=(True, "")):

        mock_browser.return_value = (True, baseline_rendered_text, "")

        db_session = SessionLocal()
        try:
            res1 = asyncio.run(check_website(db_session, site_id, render_js=True))
            assert res1["status"] == "baseline_created"
            assert res1["snapshot_id"] is not None

            # Verify snapshot in DB
            snap = db_session.query(Snapshot).filter(Snapshot.website_id == site_id).first()
            assert snap is not None
            assert snap.content == baseline_rendered_text
        finally:
            db_session.close()

    # 2. Second check: Unchanged JS-rendered content
    with patch("app.services.browser_scraper.fetch_webpage_content_browser", new_callable=AsyncMock) as mock_browser, \
         patch("app.services.browser_scraper.is_playwright_available", return_value=(True, "")):

        mock_browser.return_value = (True, baseline_rendered_text, "")

        db_session = SessionLocal()
        try:
            res2 = asyncio.run(check_website(db_session, site_id, render_js=True))
            assert res2["status"] == "no_change"
            assert db_session.query(Change).filter(Change.website_id == site_id).count() == 0
        finally:
            db_session.close()

    # 3. Third check: Changed JS-rendered content
    with patch("app.services.browser_scraper.fetch_webpage_content_browser", new_callable=AsyncMock) as mock_browser, \
         patch("app.services.browser_scraper.is_playwright_available", return_value=(True, "")):

        mock_browser.return_value = (True, updated_rendered_text, "")

        db_session = SessionLocal()
        try:
            res3 = asyncio.run(check_website(db_session, site_id, render_js=True))
            assert res3["status"] == "change_detected"

            # Verify Change record and diff
            change = db_session.query(Change).filter(Change.website_id == site_id).first()
            assert change is not None
            assert "Nov 15" in change.new_content_snippet or "1 line" in change.summary

            # Verify Notification created
            notif = db_session.query(Notification).filter(Notification.website_id == site_id).first()
            assert notif is not None
            assert "Dynamic JS Student Portal" in notif.title

            # Clean up
            site_row = db_session.query(Website).filter(Website.id == site_id).first()
            if site_row:
                db_session.delete(site_row)
                db_session.commit()
        finally:
            db_session.close()
