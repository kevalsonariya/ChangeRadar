"""Automated test suite for ChangeRadar Automatic Website Monitoring Worker."""

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, SessionLocal
from app.models.models import Website, Snapshot, Change, Notification, utc_now
from app.worker import (
    MonitoringWorker,
    is_website_due,
    get_due_websites,
    DEFAULT_LOCK_FILE,
)
from app.services.check_service import ACTIVE_CHECKS

client = TestClient(app)


def setup_module():
    """Ensure database tables are initialized before tests run."""
    init_db()


def test_worker_does_not_start_in_ordinary_api_tests():
    """Requirement: The worker does not start automatically in ordinary API tests."""
    # Health endpoint works via TestClient without starting any background worker
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"

    # Default worker lock file should NOT exist from running API calls
    assert not DEFAULT_LOCK_FILE.exists()


def test_due_website_selection_and_skipping():
    """Requirements:
    - A due website is selected for checking.
    - A website not yet due is skipped.
    - Disabled websites are skipped.
    """
    db = SessionLocal()
    try:
        now = datetime(2026, 10, 14, 12, 0, 0, tzinfo=timezone.utc)

        # Pre-clean
        for old in db.query(Website).filter(
            Website.url.in_([
                "https://never-checked.example.edu",
                "https://past-due.example.edu",
                "https://recently-checked.example.edu",
                "https://paused.example.edu",
            ])
        ).all():
            db.delete(old)
        db.commit()

        # 1. Site never checked -> Due immediately
        site_new = Website(
            name="Never Checked Portal",
            url="https://never-checked.example.edu",
            category="Academic",
            check_interval_minutes=60,
            status="active",
            last_checked_at=None,
        )

        # 2. Site checked 90 minutes ago with 60m interval -> Due
        site_due = Website(
            name="Past Due Portal",
            url="https://past-due.example.edu",
            category="Academic",
            check_interval_minutes=60,
            status="active",
            last_checked_at=now - timedelta(minutes=90),
        )

        # 3. Site checked 15 minutes ago with 60m interval -> NOT due
        site_not_due = Website(
            name="Recently Checked Portal",
            url="https://recently-checked.example.edu",
            category="Academic",
            check_interval_minutes=60,
            status="active",
            last_checked_at=now - timedelta(minutes=15),
        )

        # 4. Site disabled/paused -> Skipped regardless of time
        site_paused = Website(
            name="Paused Portal",
            url="https://paused.example.edu",
            category="Academic",
            check_interval_minutes=60,
            status="paused",
            last_checked_at=None,
        )

        db.add_all([site_new, site_due, site_not_due, site_paused])
        db.commit()
        for s in (site_new, site_due, site_not_due, site_paused):
            db.refresh(s)

        # Unit tests on is_website_due
        assert is_website_due(site_new, now=now) is True
        assert is_website_due(site_due, now=now) is True
        assert is_website_due(site_not_due, now=now) is False
        assert is_website_due(site_paused, now=now) is False

        # Test query selector get_due_websites
        due_websites = get_due_websites(db, now=now, min_interval_minutes=1)
        due_ids = [w.id for w in due_websites]

        assert site_new.id in due_ids
        assert site_due.id in due_ids
        assert site_not_due.id not in due_ids
        assert site_paused.id not in due_ids

        # Clean up test rows
        for s in (site_new, site_due, site_not_due, site_paused):
            db.delete(s)
        db.commit()

    finally:
        db.close()


def test_worker_unchanged_page_creates_no_duplicate_change():
    """Requirement: An unchanged page creates no duplicate change or notification."""
    db = SessionLocal()
    try:
        # Pre-clean
        for old in db.query(Website).filter(Website.url == "https://unchanged-worker-test.example.edu").all():
            db.delete(old)
        db.commit()

        site = Website(
            name="Unchanged Flow Test Site",
            url="https://unchanged-worker-test.example.edu",
            category="Academic",
            check_interval_minutes=10,
            status="active",
            last_checked_at=None,
        )
        db.add(site)
        db.commit()
        db.refresh(site)
        site_id = site.id
    finally:
        db.close()

    worker = MonitoringWorker(
        poll_interval=1.0,
        request_delay=0.0,
        min_interval_minutes=0,
        single_instance=False,
    )

    content = "Engineering Department Announcements: Classes start October 20."

    async def mock_fetch(url, selector):
        return True, content, ""

    with patch("app.services.check_service.fetch_webpage_content", side_effect=mock_fetch):
        # 1. First run: should create baseline snapshot
        res1 = asyncio.run(worker.check_single_website(site_id))
        assert res1["status"] == "baseline_created"

        # Verify 1 snapshot, 0 changes in DB
        db_chk = SessionLocal()
        try:
            snaps_1 = db_chk.query(Snapshot).filter(Snapshot.website_id == site_id).count()
            changes_1 = db_chk.query(Change).filter(Change.website_id == site_id).count()
            assert snaps_1 == 1
            assert changes_1 == 0
        finally:
            db_chk.close()

        # 2. Second run: content is identical -> status='no_change'
        res2 = asyncio.run(worker.check_single_website(site_id))
        assert res2["status"] == "no_change"

        # Verify snapshots count is STILL 1, changes count is STILL 0 (NO duplicates)
        db_chk2 = SessionLocal()
        try:
            snaps_2 = db_chk2.query(Snapshot).filter(Snapshot.website_id == site_id).count()
            changes_2 = db_chk2.query(Change).filter(Change.website_id == site_id).count()
            notifs_2 = db_chk2.query(Notification).filter(Notification.website_id == site_id).count()
            assert snaps_2 == 1, "Duplicate snapshot created for unchanged content!"
            assert changes_2 == 0, "False change record created for unchanged content!"
            assert notifs_2 == 0, "False notification created for unchanged content!"

            # Clean up test site
            site_row = db_chk2.query(Website).filter(Website.id == site_id).first()
            if site_row:
                db_chk2.delete(site_row)
                db_chk2.commit()
        finally:
            db_chk2.close()


def test_worker_changed_page_creates_expected_change_and_notification():
    """Requirement: A changed page creates the expected change record and notification."""
    db = SessionLocal()
    try:
        # Pre-clean
        for old in db.query(Website).filter(Website.url == "https://change-worker-test.example.edu").all():
            db.delete(old)
        db.commit()

        site = Website(
            name="Change Flow Test Site",
            url="https://change-worker-test.example.edu",
            category="Academic",
            check_interval_minutes=10,
            status="active",
            last_checked_at=None,
        )
        db.add(site)
        db.commit()
        db.refresh(site)
        site_id = site.id
    finally:
        db.close()

    worker = MonitoringWorker(
        poll_interval=1.0,
        request_delay=0.0,
        min_interval_minutes=0,
        single_instance=False,
    )

    baseline_content = "Midterm schedule pending."
    updated_content = "Midterm schedule pending.\nExam Date: Nov 18, 2026."

    async def mock_fetch_baseline(url, selector):
        return True, baseline_content, ""

    async def mock_fetch_updated(url, selector):
        return True, updated_content, ""

    # 1. Establish baseline
    with patch("app.services.check_service.fetch_webpage_content", side_effect=mock_fetch_baseline):
        res1 = asyncio.run(worker.check_single_website(site_id))
        assert res1["status"] == "baseline_created"

    # 2. Trigger check with modified content
    with patch("app.services.check_service.fetch_webpage_content", side_effect=mock_fetch_updated):
        res2 = asyncio.run(worker.check_single_website(site_id))
        assert res2["status"] == "change_detected"

    db_chk = SessionLocal()
    try:
        # Verify 2 snapshots exist
        snaps = db_chk.query(Snapshot).filter(Snapshot.website_id == site_id).all()
        assert len(snaps) == 2

        # Verify Change record exists with unified diff
        changes = db_chk.query(Change).filter(Change.website_id == site_id).all()
        assert len(changes) == 1
        assert "Exam Date" in changes[0].summary or "line" in changes[0].summary
        assert changes[0].diff_unified is not None
        assert "@@" in changes[0].diff_unified

        # Verify Notification exists
        notifs = db_chk.query(Notification).filter(Notification.website_id == site_id).all()
        assert len(notifs) >= 1
        assert notifs[0].is_read is False

        # Clean up
        site_row = db_chk.query(Website).filter(Website.id == site_id).first()
        if site_row:
            db_chk.delete(site_row)
            db_chk.commit()
    finally:
        db_chk.close()


def test_failed_request_does_not_stop_future_worker_cycles():
    """Requirement: A failed request does not stop future worker cycles."""
    db = SessionLocal()
    try:
        # Pre-clean any remnants from prior interrupted runs
        for old in db.query(Website).filter(
            Website.url.in_([
                "https://unreachable-domain-502.example.edu",
                "https://healthy-portal-200.example.edu"
            ])
        ).all():
            db.delete(old)
        db.commit()

        site_bad = Website(
            name="Unreachable Portal",
            url="https://unreachable-domain-502.example.edu",
            category="Academic",
            check_interval_minutes=5,
            status="active",
            last_checked_at=None,
        )
        site_good = Website(
            name="Healthy Portal",
            url="https://healthy-portal-200.example.edu",
            category="Academic",
            check_interval_minutes=5,
            status="active",
            last_checked_at=None,
        )
        db.add_all([site_bad, site_good])
        db.commit()
        db.refresh(site_bad)
        db.refresh(site_good)
        bad_id = site_bad.id
        good_id = site_good.id
    finally:
        db.close()

    worker = MonitoringWorker(
        poll_interval=1.0,
        request_delay=0.0,
        min_interval_minutes=0,
        single_instance=False,
    )

    async def mock_fetch_routing(url, selector):
        if "unreachable" in url:
            return False, "", "Remote web server returned HTTP 502 Bad Gateway"
        return True, "Healthy portal content verified.", ""

    with patch("app.services.check_service.fetch_webpage_content", side_effect=mock_fetch_routing), \
         patch("app.worker.get_due_websites", return_value=[site_bad, site_good]):
        # Run worker cycle 1 (site_bad fails, site_good succeeds)
        stats = asyncio.run(worker.run_once())

        # Both sites were processed in this cycle
        assert stats["checked"] == 2
        assert stats["errors"] == 1
        assert stats["baselines"] == 1

        # Check DB state
        db_chk = SessionLocal()
        try:
            bad_row = db_chk.query(Website).filter(Website.id == bad_id).first()
            good_row = db_chk.query(Website).filter(Website.id == good_id).first()

            # Failed site was marked error without crashing worker
            assert bad_row.status == "error"
            assert bad_row.last_checked_at is not None

            # Healthy site captured baseline cleanly
            assert good_row.status == "active"
            assert good_row.last_checked_at is not None
        finally:
            db_chk.close()

        # Run worker cycle 2: proves worker continues executing subsequent cycles
        stats2 = asyncio.run(worker.run_once())
        assert stats2["checked"] == 2
        assert stats2["errors"] == 1

        # Clean up
        db_chk = SessionLocal()
        try:
            bad_row = db_chk.query(Website).filter(Website.id == bad_id).first()
            good_row = db_chk.query(Website).filter(Website.id == good_id).first()
            if bad_row:
                db_chk.delete(bad_row)
            if good_row:
                db_chk.delete(good_row)
            db_chk.commit()
        finally:
            db_chk.close()


def test_two_checks_cannot_overlap_for_same_website():
    """Requirement: Two checks cannot overlap for the same website within a worker."""
    worker = MonitoringWorker(
        poll_interval=1.0,
        request_delay=0.0,
        single_instance=False,
    )

    test_site_id = 99999

    # Simulate check already in progress in worker registry
    worker.in_progress.add(test_site_id)
    try:
        res = asyncio.run(worker.check_single_website(test_site_id))
        assert res["status"] == "skipped"
        assert "already in progress" in res["message"]
    finally:
        worker.in_progress.discard(test_site_id)

    # Simulate in-process ACTIVE_CHECKS guard in check_service
    ACTIVE_CHECKS.add(test_site_id)
    try:
        from fastapi import HTTPException
        db = SessionLocal()
        try:
            with pytest.raises(HTTPException) as exc_info:
                from app.services.check_service import check_website
                asyncio.run(check_website(db, test_site_id))
            assert exc_info.value.status_code == 409
            assert "already in progress" in exc_info.value.detail
        finally:
            db.close()
    finally:
        ACTIVE_CHECKS.discard(test_site_id)


def test_single_instance_lock_coordination(tmp_path):
    """Requirement: Single worker instance coordination via lock file."""
    lock_file = tmp_path / "test_worker.lock"

    worker1 = MonitoringWorker(single_instance=True, lock_file_path=lock_file)
    worker2 = MonitoringWorker(single_instance=True, lock_file_path=lock_file)

    # Worker 1 acquires lock
    assert worker1.acquire_instance_lock() is True
    assert lock_file.exists()

    # Worker 2 attempts to acquire lock while Worker 1 is alive -> Rejection
    assert worker2.acquire_instance_lock() is False

    # Worker 1 releases lock
    worker1.release_instance_lock()
    assert not lock_file.exists()

    # Now Worker 2 can acquire lock
    assert worker2.acquire_instance_lock() is True
    worker2.release_instance_lock()
    assert not lock_file.exists()
