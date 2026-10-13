"""Comprehensive verification test suite for SSRF protection, crawling, baseline snapshots,
and change detection in ChangeRadar.
"""

import sys
from pathlib import Path
from unittest.mock import patch

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, SessionLocal
from app.models.models import Website, Snapshot, Change
from app.services.scraper import is_safe_url, normalize_html_content
from app.services.differ import compute_text_diff

client = TestClient(app)


def setup_module():
    """Ensure database tables are initialized before tests run."""
    init_db()


def test_ssrf_protection_rules():
    """Verify that private, loopback, and local network destinations are blocked."""
    # 1. Localhost
    safe, msg = is_safe_url("http://localhost:8000/api/websites")
    assert not safe
    assert "SSRF" in msg or "blocked" in msg

    # 2. Loopback 127.0.0.1
    safe, msg = is_safe_url("http://127.0.0.1:8000/secret")
    assert not safe
    assert "loopback" in msg or "blocked" in msg

    # 3. Private 192.168.x.x
    safe, msg = is_safe_url("http://192.168.1.100/admin")
    assert not safe
    assert "private" in msg or "blocked" in msg

    # 4. Cloud metadata IP 169.254.169.254
    safe, msg = is_safe_url("http://169.254.169.254/latest/meta-data/")
    assert not safe
    assert "link-local" in msg or "blocked" in msg

    # 5. Invalid scheme
    safe, msg = is_safe_url("ftp://example.com/file.txt")
    assert not safe
    assert "scheme" in msg


def test_html_normalization_and_noise_removal():
    """Verify scripts, styles, and whitespace noise are stripped cleanly."""
    dirty_html = """
    <html>
      <head>
        <style>body { color: red; }</style>
        <script>alert('bad');</script>
      </head>
      <body>
        <svg><path d="M0 0"/></svg>
        <div id="content">
          <h1>Examination Announcement</h1>
          <p>   All students must submit assignments by Oct 25.   </p>
        </div>
      </body>
    </html>
    """
    ok, text, err = normalize_html_content(dirty_html)
    assert ok
    assert "body { color: red; }" not in text
    assert "alert('bad')" not in text
    assert "Examination Announcement" in text
    assert "All students must submit assignments by Oct 25." in text


def test_html_selector_isolation():
    """Verify selector targeting extracts only the requested element."""
    html = """
    <div class="sidebar">Ignore this sidebar update</div>
    <div id="notice-board">
      <h2>Important Notice</h2>
      <p>Exam dates finalized</p>
    </div>
    """
    ok, text, _ = normalize_html_content(html, selector="#notice-board")
    assert ok
    assert "Important Notice" in text
    assert "Ignore this sidebar update" not in text


def test_differ_detects_changes_accurately():
    """Verify difflib computes additions, deletions, and modifications."""
    old_content = "Line 1: Announcement\nLine 2: Date: Oct 15\nLine 3: Venue: Hall A"
    new_content = "Line 1: Announcement\nLine 2: Date: Oct 20 (POSTPONED)\nLine 3: Venue: Hall A\nLine 4: Bring Hall Ticket"

    diff = compute_text_diff(old_content, new_content)
    assert diff["has_changes"] is True
    assert diff["change_type"] == "modification"
    assert diff["additions_count"] >= 1
    assert diff["deletions_count"] >= 1
    assert "Oct 20 (POSTPONED)" in diff["new_content_snippet"]
    assert "Oct 15" in diff["old_content_snippet"]


def test_full_check_workflow_baseline_nochange_and_detected():
    """End-to-end test of:
    1. First check -> baseline created (no change record)
    2. Second check -> unchanged content (no change record)
    3. Third check -> modified content (change record and notification created)
    """
    # Create test website
    site_payload = {
        "name": "Live Notice Board Test",
        "url": "https://testnotices.college.edu/circulars",
        "category": "University",
        "check_interval_minutes": 30
    }
    create_res = client.post("/websites", json=site_payload)
    assert create_res.status_code == 201
    site_id = create_res.json()["id"]

    db = SessionLocal()
    try:
        # --- 1. FIRST CHECK: Baseline creation ---
        baseline_html = "<h1>Winter 2026 Practical Exam</h1><p>Submission deadline: Oct 20</p>"
        with patch("app.services.check_service.fetch_webpage_content", return_value=(True, "Winter 2026 Practical Exam\nSubmission deadline: Oct 20", "")):
            res_check1 = client.post(f"/websites/{site_id}/check")
            assert res_check1.status_code == 200
            data1 = res_check1.json()
            assert data1["status"] == "baseline_created"
            assert data1["snapshot_id"] is not None
            assert data1["change_id"] is None

        # Verify in DB: 1 snapshot, 0 changes
        snap_count = db.query(Snapshot).filter(Snapshot.website_id == site_id).count()
        change_count = db.query(Change).filter(Change.website_id == site_id).count()
        assert snap_count == 1
        assert change_count == 0

        # --- 2. SECOND CHECK: Unchanged content ---
        with patch("app.services.check_service.fetch_webpage_content", return_value=(True, "Winter 2026 Practical Exam\nSubmission deadline: Oct 20", "")):
            res_check2 = client.post(f"/websites/{site_id}/check")
            assert res_check2.status_code == 200
            data2 = res_check2.json()
            assert data2["status"] == "no_change"
            assert data2["change_id"] is None

        # Verify still 0 changes
        change_count_after_same = db.query(Change).filter(Change.website_id == site_id).count()
        assert change_count_after_same == 0

        # --- 3. THIRD CHECK: Changed content ---
        updated_content = "Winter 2026 Practical Exam\nSubmission deadline: Oct 28 (EXTENDED)\nHall tickets available Oct 22"
        with patch("app.services.check_service.fetch_webpage_content", return_value=(True, updated_content, "")):
            res_check3 = client.post(f"/websites/{site_id}/check")
            assert res_check3.status_code == 200
            data3 = res_check3.json()
            assert data3["status"] == "change_detected"
            assert data3["change_id"] is not None
            change_id = data3["change_id"]

        # Verify in DB: 2 snapshots, 1 change
        snap_count_after_change = db.query(Snapshot).filter(Snapshot.website_id == site_id).count()
        change_count_after_change = db.query(Change).filter(Change.website_id == site_id).count()
        assert snap_count_after_change == 2
        assert change_count_after_change == 1

        # --- 4. TEST CHANGE HISTORY ENDPOINTS ---
        # GET /changes
        res_changes = client.get("/changes")
        assert res_changes.status_code == 200
        all_changes = res_changes.json()
        assert any(c["id"] == change_id for c in all_changes)

        # GET /changes/{change_id}
        res_detail = client.get(f"/changes/{change_id}")
        assert res_detail.status_code == 200
        detail_data = res_detail.json()
        assert detail_data["id"] == change_id
        assert detail_data["website_id"] == site_id
        assert "EXTENDED" in detail_data["new_content_snippet"]
        assert detail_data["diff_unified"] is not None

        # PATCH /changes/{change_id}/read
        res_read = client.patch(f"/changes/{change_id}/read")
        assert res_read.status_code == 200
        assert res_read.json()["is_read"] is True

        # GET /websites/{id}/changes
        res_site_changes = client.get(f"/websites/{site_id}/changes")
        assert res_site_changes.status_code == 200
        assert len(res_site_changes.json()) == 1

    finally:
        # Cleanup
        client.delete(f"/websites/{site_id}")
        db.close()


def test_failed_fetch_handling_and_no_empty_snapshots():
    """Verify that a network failure marks website status='error' and creates NO snapshot."""
    site_payload = {
        "name": "Failing Endpoint Test",
        "url": "https://broken-server.college.edu/feed",
        "category": "General",
    }
    create_res = client.post("/websites", json=site_payload)
    site_id = create_res.json()["id"]

    db = SessionLocal()
    try:
        # Mock connection failure
        with patch("app.services.check_service.fetch_webpage_content", return_value=(False, "", "Connection timed out")):
            res = client.post(f"/websites/{site_id}/check")
            assert res.status_code == 502
            assert "Connection timed out" in res.json()["detail"]

        # Confirm NO snapshot was created
        snapshots = db.query(Snapshot).filter(Snapshot.website_id == site_id).all()
        assert len(snapshots) == 0

        # Confirm website status was updated to 'error'
        site = db.query(Website).filter(Website.id == site_id).first()
        assert site.status == "error"
        assert site.last_checked_at is not None

    finally:
        client.delete(f"/websites/{site_id}")
        db.close()
