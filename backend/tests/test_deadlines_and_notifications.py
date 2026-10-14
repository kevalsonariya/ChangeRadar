"""Test suite for persistent deadlines, notification actions, and automated deadline extraction."""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, SessionLocal
from app.models.models import Notification, Website, Deadline, utc_now
from app.services.deadline_extractor import (
    extract_deadlines_from_text,
    normalize_date_string,
    calculate_deadline_metrics,
    sync_extracted_deadlines,
)

client = TestClient(app)


def setup_module():
    """Ensure database tables are initialized before tests run."""
    init_db()


def test_deadline_crud_workflow():
    # 1. Create a deadline (POST /api/deadlines)
    payload = {
        "title": "Semester Final Exam Registration",
        "due_date": "2026-12-15",
        "priority": "high",
        "category": "Exams",
        "description": "Register on the university portal before 5 PM",
        "source_url": "https://university.edu/exams",
    }
    res_create = client.post("/api/deadlines", json=payload)
    assert res_create.status_code == 201
    created = res_create.json()
    deadline_id = created["id"]
    assert created["title"] == payload["title"]
    assert created["due_date"] == "2026-12-15"
    assert created["priority"] == "high"
    assert created["is_completed"] is False
    assert created["days_left"] > 0

    # 2. Retrieve deadline (GET /api/deadlines/{id})
    res_get = client.get(f"/api/deadlines/{deadline_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == deadline_id

    # 3. List deadlines (GET /api/deadlines)
    res_list = client.get("/api/deadlines")
    assert res_list.status_code == 200
    items = res_list.json()
    assert any(d["id"] == deadline_id for d in items)

    # 4. Update deadline (PUT /api/deadlines/{id})
    res_update = client.put(f"/api/deadlines/{deadline_id}", json={
        "title": "Updated Final Exam Registration Deadline",
        "priority": "medium",
    })
    assert res_update.status_code == 200
    updated = res_update.json()
    assert updated["title"] == "Updated Final Exam Registration Deadline"
    assert updated["priority"] == "medium"

    # 5. Mark deadline completed (PATCH /api/deadlines/{id}/complete)
    res_toggle = client.patch(f"/api/deadlines/{deadline_id}/complete", json={"is_completed": True})
    assert res_toggle.status_code == 200
    toggled = res_toggle.json()
    assert toggled["is_completed"] is True
    assert toggled["status"] == "completed"

    # 6. Reopen deadline (PATCH /api/deadlines/{id}/complete with is_completed=False)
    res_reopen = client.patch(f"/api/deadlines/{deadline_id}/complete", json={"is_completed": False})
    assert res_reopen.status_code == 200
    reopened = res_reopen.json()
    assert reopened["is_completed"] is False
    assert reopened["status"] != "completed"

    # 7. Delete deadline (DELETE /api/deadlines/{id})
    res_del = client.delete(f"/api/deadlines/{deadline_id}")
    assert res_del.status_code == 200

    # 8. Verify deletion (GET /api/deadlines/{id} -> 404)
    res_after_del = client.get(f"/api/deadlines/{deadline_id}")
    assert res_after_del.status_code == 404


def test_deadline_validation_errors():
    # Blank title
    res_bad_title = client.post("/api/deadlines", json={
        "title": "   ",
        "due_date": "2026-10-30",
    })
    assert res_bad_title.status_code == 422

    # Invalid date format
    res_bad_date = client.post("/api/deadlines", json={
        "title": "Valid Title",
        "due_date": "someday-in-autumn",
    })
    assert res_bad_date.status_code == 422

    # Invalid priority
    res_bad_prio = client.post("/api/deadlines", json={
        "title": "Valid Title",
        "due_date": "2026-10-30",
        "priority": "ultra-urgent",
    })
    assert res_bad_prio.status_code == 422


def test_notification_actions():
    db = SessionLocal()
    try:
        # Create test notifications directly
        notif1 = Notification(
            type="change",
            title="Test Change Alert 1",
            message="Content modified on test site",
            is_read=False,
            created_at=utc_now(),
        )
        notif2 = Notification(
            type="system",
            title="Test System Alert 2",
            message="Watchlist scan complete",
            is_read=False,
            created_at=utc_now(),
        )
        db.add_all([notif1, notif2])
        db.commit()
        db.refresh(notif1)
        db.refresh(notif2)

        id1 = notif1.id
        id2 = notif2.id
    finally:
        db.close()

    # 1. List notifications
    res_list = client.get("/api/notifications")
    assert res_list.status_code == 200
    notifs = res_list.json()
    assert any(n["id"] == id1 for n in notifs)

    # 2. Mark one notification as read (PATCH /api/notifications/{id}/read)
    res_read = client.patch(f"/api/notifications/{id1}/read")
    assert res_read.status_code == 200
    assert res_read.json()["is_read"] is True

    # Check persistence
    db2 = SessionLocal()
    try:
        reloaded1 = db2.query(Notification).filter(Notification.id == id1).first()
        assert reloaded1.is_read is True
        reloaded2 = db2.query(Notification).filter(Notification.id == id2).first()
        assert reloaded2.is_read is False
    finally:
        db2.close()

    # 3. Mark all as read (POST /api/notifications/read-all)
    res_read_all = client.post("/api/notifications/read-all")
    assert res_read_all.status_code == 200

    db3 = SessionLocal()
    try:
        all_unread = db3.query(Notification).filter(Notification.is_read.is_(False)).count()
        assert all_unread == 0
    finally:
        db3.close()


def test_deadline_extraction_service():
    # Text with both genuine deadline phrases and incidental non-deadline dates
    sample_text = """
    Welcome to Government Engineering College.
    Published on January 15, 2024.
    Recent news: Campus was visited on March 10, 2025.
    
    IMPORTANT NOTICE:
    Submission Deadline: Oct 25, 2026
    Final Exam Date: 2026-11-15
    Application Last Date: 12/05/2026
    
    Contact us at office@college.edu.
    """

    extracted = extract_deadlines_from_text(sample_text)
    # Incidental dates (Published on..., Campus was visited...) should NOT be extracted as deadlines
    # Only lines with keywords like Deadline, Exam Date, Last Date should be extracted
    assert len(extracted) == 3

    dates_extracted = [item["due_date"] for item in extracted]
    assert "2026-10-25" in dates_extracted
    assert "2026-11-15" in dates_extracted

    # Test deduplication across repeated checks
    db = SessionLocal()
    try:
        # Create temporary site
        site = Website(
            name="Extraction Test Site",
            url="https://test-extraction.example.edu",
            category="Academic",
            status="active",
            created_at=utc_now(),
        )
        db.add(site)
        db.commit()
        db.refresh(site)

        # First run: should insert items
        first_sync = sync_extracted_deadlines(db, extracted, site.id, source_url=site.url)
        assert len(first_sync) == 3

        # Second run with same extracted items: should insert 0 duplicates
        second_sync = sync_extracted_deadlines(db, extracted, site.id, source_url=site.url)
        assert len(second_sync) == 0

        # Clean up test site and its deadlines
        db.delete(site)
        db.commit()
    finally:
        db.close()
