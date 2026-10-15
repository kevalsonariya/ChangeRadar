"""Automated tests for Authentication, Authorization, Email Verification, and User Notifications.

Covers:
- Registration success and duplicate email rejection.
- Password hashing security and login success/failure.
- Email verification success, expiry, and token reuse rejection.
- Protected routes, session persistence, and logout behavior.
- Cross-user access denial (websites, deadlines, notifications).
- Verified user's email receiving mocked alert.
- Disabled email notification preferences suppressing delivery.
- SMTP failure not breaking monitoring or database persistence.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import init_db, SessionLocal
from app.models.models import User, Website, Deadline, Notification, EmailVerificationToken, utc_now
from app.services import auth_service, check_service, email_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    auth_service.reset_rate_limits()


def test_user_registration_success_and_duplicate_rejection():
    email = f"student_{datetime.now().timestamp()}@example.edu"
    payload = {
        "name": "Alice Johnson",
        "email": email,
        "password": "SecurePassword123!",
        "confirm_password": "SecurePassword123!"
    }
    
    # 1. Successful registration
    with patch("app.services.email_service.send_verification_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (True, None)
        res = client.post("/auth/register", json=payload)
        assert res.status_code == 201
        data = res.json()
        assert data["email"] == email.lower()
        assert data["name"] == "Alice Johnson"
        assert data["email_verified"] is False
        assert data["email_notifications_enabled"] is True
        assert "password" not in data
        assert "password_hash" not in data
        assert auth_service.COOKIE_NAME in res.cookies

    # 2. Duplicate registration rejection
    res_dup = client.post("/auth/register", json=payload)
    assert res_dup.status_code == 409
    assert "already exists" in res_dup.json()["detail"]


def test_password_hashing_and_login_validation():
    db = SessionLocal()
    email = f"bob_{datetime.now().timestamp()}@example.edu"
    raw_password = "SecretPassword456!"
    
    # Register Bob
    res = client.post("/auth/register", json={
        "name": "Bob Smith",
        "email": email,
        "password": raw_password,
        "confirm_password": raw_password
    })
    assert res.status_code == 201
    
    # Verify password was hashed (never plaintext in DB)
    bob_user = db.query(User).filter(User.email == email).first()
    assert bob_user is not None
    assert bob_user.password_hash != raw_password
    assert "$" in bob_user.password_hash  # PBKDF2 salt$hash format
    assert auth_service.verify_password(raw_password, bob_user.password_hash) is True
    assert auth_service.verify_password("WrongPassword!", bob_user.password_hash) is False
    db.close()

    # Login with wrong password -> 401
    res_fail = client.post("/auth/login", json={
        "email": email,
        "password": "WrongPassword!"
    })
    assert res_fail.status_code == 401
    assert "Invalid email or password" in res_fail.json()["detail"]

    # Login with correct password -> 200 and set cookie
    res_ok = client.post("/auth/login", json={
        "email": email,
        "password": raw_password
    })
    assert res_ok.status_code == 200
    assert auth_service.COOKIE_NAME in res_ok.cookies


def test_email_verification_workflow_and_token_reuse():
    db = SessionLocal()
    email = f"charlie_{datetime.now().timestamp()}@example.edu"
    
    # Register user
    res = client.post("/auth/register", json={
        "name": "Charlie Brown",
        "email": email,
        "password": "Password789!",
        "confirm_password": "Password789!"
    })
    assert res.status_code == 201
    user_id = res.json()["id"]

    # Find the verification token in DB
    token_row = db.query(EmailVerificationToken).filter(EmailVerificationToken.user_id == user_id).first()
    assert token_row is not None
    valid_token = token_row.token

    # 1. Invalid token rejection
    res_invalid = client.post("/auth/verify-email", json={"token": "completely-invalid-token"})
    assert res_invalid.status_code == 400
    assert "Invalid email verification token" in res_invalid.json()["detail"]

    # 2. Valid token verification
    res_verify = client.post("/auth/verify-email", json={"token": valid_token})
    assert res_verify.status_code == 200
    assert res_verify.json()["email_verified"] is True

    # 3. Prevent token reuse
    res_reuse = client.post("/auth/verify-email", json={"token": valid_token})
    assert res_reuse.status_code == 400
    assert "already been used" in res_reuse.json()["detail"]

    # 4. Expired token rejection
    expired_token = auth_service.create_verification_token(db, token_row.user)
    db_exp_token = db.query(EmailVerificationToken).filter(EmailVerificationToken.token == expired_token).first()
    db_exp_token.expires_at = utc_now() - timedelta(hours=2)
    db.commit()

    res_exp = client.post("/auth/verify-email", json={"token": expired_token})
    assert res_exp.status_code == 400
    assert "expired" in res_exp.json()["detail"]
    db.close()


def test_session_lifecycle_me_and_logout():
    email = f"diana_{datetime.now().timestamp()}@example.edu"
    reg_res = client.post("/auth/register", json={
        "name": "Diana Prince",
        "email": email,
        "password": "SuperSecretPassword1!",
        "confirm_password": "SuperSecretPassword1!"
    })
    assert reg_res.status_code == 201
    session_cookie = reg_res.cookies[auth_service.COOKIE_NAME]

    # Authenticated /auth/me
    client.cookies.set(auth_service.COOKIE_NAME, session_cookie)
    res_me = client.get("/auth/me")
    assert res_me.status_code == 200
    assert res_me.json()["email"] == email

    # Update settings
    res_patch = client.patch("/auth/settings", json={"email_notifications_enabled": False})
    assert res_patch.status_code == 200
    assert res_patch.json()["email_notifications_enabled"] is False

    # Logout
    res_logout = client.post("/auth/logout")
    assert res_logout.status_code == 200

    # Next /auth/me should fail with 401
    res_me_after = client.get("/auth/me")
    assert res_me_after.status_code == 401
    client.cookies.clear()


def test_cross_user_access_denial():
    # Create User 1
    u1_email = f"user1_{datetime.now().timestamp()}@example.edu"
    u1_reg = client.post("/auth/register", json={
        "name": "User One",
        "email": u1_email,
        "password": "Password111!",
        "confirm_password": "Password111!"
    })
    assert u1_reg.status_code == 201
    u1_cookie = u1_reg.cookies[auth_service.COOKIE_NAME]

    # Create User 2
    u2_email = f"user2_{datetime.now().timestamp()}@example.edu"
    u2_reg = client.post("/auth/register", json={
        "name": "User Two",
        "email": u2_email,
        "password": "Password222!",
        "confirm_password": "Password222!"
    })
    assert u2_reg.status_code == 201
    u2_cookie = u2_reg.cookies[auth_service.COOKIE_NAME]

    # User 1 creates a website and deadline
    client.cookies.set(auth_service.COOKIE_NAME, u1_cookie)
    site_url = f"https://u1-site-{datetime.now().timestamp()}.edu"
    res_site = client.post("/websites", json={
        "name": "User 1 Private Portal",
        "url": site_url,
        "category": "Private"
    })
    assert res_site.status_code == 201
    u1_site_id = res_site.json()["id"]

    res_dl = client.post("/deadlines", json={
        "title": "User 1 Secret Exam",
        "due_date": "2026-11-15",
        "priority": "high",
        "website_id": u1_site_id
    })
    assert res_dl.status_code == 201
    u1_dl_id = res_dl.json()["id"]

    # Switch to User 2
    client.cookies.set(auth_service.COOKIE_NAME, u2_cookie)

    # User 2 tries to GET User 1's website -> 404
    res_denied_site = client.get(f"/websites/{u1_site_id}")
    assert res_denied_site.status_code == 404

    # User 2 tries to DELETE User 1's website -> 404
    res_denied_del = client.delete(f"/websites/{u1_site_id}")
    assert res_denied_del.status_code == 404

    # User 2 tries to GET User 1's deadline -> 404
    res_denied_dl = client.get(f"/deadlines/{u1_dl_id}")
    assert res_denied_dl.status_code == 404

    # User 2 tries to complete User 1's deadline -> 404
    res_denied_toggle = client.patch(f"/deadlines/{u1_dl_id}/complete")
    assert res_denied_toggle.status_code == 404

    # User 2 tries to DELETE User 1's deadline -> 404
    res_denied_dl_del = client.delete(f"/deadlines/{u1_dl_id}")
    assert res_denied_dl_del.status_code == 404

    client.cookies.clear()


def test_email_notification_delivery_and_preference_suppression():
    db = SessionLocal()
    email = f"verified_user_{datetime.now().timestamp()}@example.edu"
    
    # 1. Create verified user with notifications enabled
    user = User(
        name="Elena Rostova",
        email=email,
        password_hash=auth_service.hash_password("Password999!"),
        email_verified=True,
        email_notifications_enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # 2. Create website belonging to this user
    test_url = f"https://portal-{datetime.now().timestamp()}.edu/announcements"
    site = Website(
        user_id=user.id,
        name="Elena Exam Watch",
        url=test_url,
        category="Academics",
        check_interval_minutes=60,
        status="active"
    )
    db.add(site)
    db.commit()
    db.refresh(site)

    # Step A: Baseline check (mocked fetch)
    with patch("app.services.check_service.fetch_webpage_content", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = (True, "Exam schedule: Midterms start Nov 10", "")
        res1 = asyncio.run(check_service.check_website(db, site.id))
        assert res1["status"] == "baseline_created"

    # Step B: Second check with content change -> Email alert MUST be sent to user's email
    with patch("app.services.check_service.fetch_webpage_content", new_callable=AsyncMock) as mock_fetch, \
         patch("app.services.email_service.send_change_alert_email", new_callable=AsyncMock) as mock_email:
        mock_fetch.return_value = (True, "Exam schedule: Midterms postponed to Nov 20", "")
        mock_email.return_value = (True, None)

        res2 = asyncio.run(check_service.check_website(db, site.id))
        assert res2["status"] == "change_detected"
        
        # Verify email was dispatched to the owning user's verified address
        mock_email.assert_called_once()
        args, kwargs = mock_email.call_args
        assert kwargs["recipient_email"] == email
        assert kwargs["website_name"] == "Elena Exam Watch"

    # Step C: Disable user's email notifications preference -> Delivery MUST be suppressed
    user.email_notifications_enabled = False
    db.commit()

    with patch("app.services.check_service.fetch_webpage_content", new_callable=AsyncMock) as mock_fetch, \
         patch("app.services.email_service.send_change_alert_email", new_callable=AsyncMock) as mock_email:
        mock_fetch.return_value = (True, "Exam schedule: Final update Nov 25", "")
        
        res3 = asyncio.run(check_service.check_website(db, site.id))
        assert res3["status"] == "change_detected"
        mock_email.assert_not_called()

    # Step D: SMTP failure must NOT break monitoring or database persistence
    user.email_notifications_enabled = True
    db.commit()

    with patch("app.services.check_service.fetch_webpage_content", new_callable=AsyncMock) as mock_fetch, \
         patch("app.services.email_service.send_change_alert_email", side_effect=Exception("SMTP Connection Timeout")):
        mock_fetch.return_value = (True, "Exam schedule: Final update Dec 1", "")
        
        res4 = asyncio.run(check_service.check_website(db, site.id))
        assert res4["status"] == "change_detected"
        assert res4["change_id"] is not None

    db.close()


def test_deadline_created_email_notification():
    """Verify email is dispatched when a deadline is added for a verified user with email notifications enabled."""
    db = SessionLocal()
    email = f"student_dl_{datetime.now().timestamp()}@example.edu"
    user = User(
        name="Diana Prince",
        email=email,
        password_hash=auth_service.hash_password("Pass123!"),
        email_verified=True,
        email_notifications_enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create session
    session_token = auth_service.create_user_session(db, user)

    # 1. Successful deadline creation dispatches confirmation email
    with patch("app.services.email_service.send_deadline_created_email", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = (True, None)
        headers = {"Authorization": f"Bearer {session_token}"}
        res = client.post(
            "/api/deadlines",
            json={
                "title": "Quantum Mechanics Problem Set",
                "due_date": "2026-11-20",
                "priority": "high",
                "category": "Physics",
                "description": "Submit online via university portal"
            },
            headers=headers
        )
        assert res.status_code == 201
        data = res.json()
        assert data["title"] == "Quantum Mechanics Problem Set"
        assert data["reminded_48h"] is False

        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args
        assert kwargs["recipient_email"] == email
        assert kwargs["title"] == "Quantum Mechanics Problem Set"
        assert kwargs["priority"] == "high"

    # 2. Disabled email notifications suppresses deadline created email
    user.email_notifications_enabled = False
    db.commit()

    with patch("app.services.email_service.send_deadline_created_email", new_callable=AsyncMock) as mock_send_suppressed:
        res2 = client.post(
            "/api/deadlines",
            json={
                "title": "Electrodynamics Quiz",
                "due_date": "2026-11-25",
                "priority": "medium",
                "category": "Physics"
            },
            headers=headers
        )
        assert res2.status_code == 201
        mock_send_suppressed.assert_not_called()

    db.close()


def test_deadline_reminder_evaluation_and_duplicate_suppression():
    """Verify reminders trigger at 48h, 24h, and 12h marks without duplicate delivery."""
    from datetime import timezone
    from app.services import deadline_reminder_service

    db = SessionLocal()
    email = f"student_reminder_{datetime.now().timestamp()}@example.edu"
    user = User(
        name="Bruce Wayne",
        email=email,
        password_hash=auth_service.hash_password("Pass123!"),
        email_verified=True,
        email_notifications_enabled=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create a deadline due in 40 hours from simulated 'now'
    base_time = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)
    due_datetime = base_time + timedelta(hours=40)
    due_date_iso = due_datetime.strftime("%Y-%m-%dT%H:%M:%SZ")

    dl = Deadline(
        user_id=user.id,
        title="Final Thesis Draft",
        due_date=due_date_iso,
        priority="high",
        category="Academic",
        is_completed=False,
    )
    db.add(dl)
    db.commit()
    db.refresh(dl)

    # Phase 1: At 40 hours remaining, 48-hour threshold must fire
    with patch("app.services.email_service.send_deadline_reminder_email", new_callable=AsyncMock) as mock_reminder:
        mock_reminder.return_value = (True, None)
        dispatched = asyncio.run(deadline_reminder_service.process_deadline_reminders(db, now=base_time))
        assert len(dispatched) == 1
        assert dispatched[0]["threshold"] == "48h"
        assert dispatched[0]["email_sent"] is True

        mock_reminder.assert_called_once()
        _, kwargs = mock_reminder.call_args
        assert kwargs["recipient_email"] == email
        assert "48 hours" in kwargs["hours_label"]

    db.refresh(dl)
    assert dl.reminded_48h is True
    assert dl.reminded_24h is False
    assert dl.reminded_12h is False

    # Phase 2: Duplicate check at same time -> must not fire duplicate
    with patch("app.services.email_service.send_deadline_reminder_email", new_callable=AsyncMock) as mock_reminder_dup:
        dispatched_dup = asyncio.run(deadline_reminder_service.process_deadline_reminders(db, now=base_time))
        assert len(dispatched_dup) == 0
        mock_reminder_dup.assert_not_called()

    # Phase 3: Advance time so 20 hours remain -> 24-hour threshold must fire
    now_20h = due_datetime - timedelta(hours=20)
    with patch("app.services.email_service.send_deadline_reminder_email", new_callable=AsyncMock) as mock_reminder_24h:
        mock_reminder_24h.return_value = (True, None)
        dispatched_24h = asyncio.run(deadline_reminder_service.process_deadline_reminders(db, now=now_20h))
        assert len(dispatched_24h) == 1
        assert dispatched_24h[0]["threshold"] == "24h"
        mock_reminder_24h.assert_called_once()
        _, kwargs = mock_reminder_24h.call_args
        assert "24 hours" in kwargs["hours_label"]

    db.refresh(dl)
    assert dl.reminded_24h is True
    assert dl.reminded_12h is False

    # Phase 4: Advance time so 8 hours remain -> 12-hour threshold must fire
    now_8h = due_datetime - timedelta(hours=8)
    with patch("app.services.email_service.send_deadline_reminder_email", new_callable=AsyncMock) as mock_reminder_12h:
        mock_reminder_12h.return_value = (True, None)
        dispatched_12h = asyncio.run(deadline_reminder_service.process_deadline_reminders(db, now=now_8h))
        assert len(dispatched_12h) == 1
        assert dispatched_12h[0]["threshold"] == "12h"
        mock_reminder_12h.assert_called_once()
        _, kwargs = mock_reminder_12h.call_args
        assert "12 hours" in kwargs["hours_label"]

    db.refresh(dl)
    assert dl.reminded_12h is True

    # Phase 5: Mark completed -> no further reminders even if checked
    dl.is_completed = True
    db.commit()
    with patch("app.services.email_service.send_deadline_reminder_email", new_callable=AsyncMock) as mock_completed:
        dispatched_completed = asyncio.run(deadline_reminder_service.process_deadline_reminders(db, now=now_8h))
        assert len(dispatched_completed) == 0
        mock_completed.assert_not_called()

    db.close()


def test_check_reminders_api_endpoint():
    """Verify manual or scheduled trigger endpoint /api/deadlines/check-reminders works."""
    with patch("app.services.deadline_reminder_service.process_deadline_reminders", new_callable=AsyncMock) as mock_proc:
        mock_proc.return_value = [{"deadline_id": 99, "threshold": "24h", "email_sent": True}]
        res = client.post("/api/deadlines/check-reminders")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["reminders_dispatched"] == 1

