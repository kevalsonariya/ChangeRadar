"""Automated deadline reminder evaluation and email alert delivery service.

Periodically evaluates upcoming deadlines and dispatches reminder notifications
and emails at 48 hours, 24 hours, and 12 hours before the due date without duplicate delivery.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from ..models.models import Deadline, Notification, User, utc_now
from . import email_service

logger = logging.getLogger("changeradar.deadline_reminders")


def parse_deadline_due_datetime(due_date_str: str) -> Optional[datetime]:
    """Parse a stored deadline due date string into a timezone-aware UTC datetime.

    Supports:
    - ISO datetime strings (e.g., '2026-10-25T14:30:00Z', '2026-10-25T14:30:00')
    - ISO date strings (e.g., '2026-10-25' -> defaults to 23:59:59 UTC on that day)
    - Standard textual dates (e.g., 'Oct 25, 2026', '25-10-2026')
    """
    if not due_date_str or not isinstance(due_date_str, str):
        return None

    cleaned = due_date_str.strip()

    # Try ISO fromisoformat first
    try:
        dt = datetime.fromisoformat(cleaned.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        pass

    # Try common explicit datetime formats
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
    ):
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    # Date-only formats: treat deadline as due at the end of that day (23:59:59 UTC)
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            d = datetime.strptime(cleaned, fmt).date()
            return datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


async def process_deadline_reminders(
    db: Session,
    now: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Scan all active uncompleted deadlines and dispatch 48h, 24h, and 12h reminders.

    Prevents duplicate delivery by persisting reminded_* flags on each Deadline.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    # Query all active, uncompleted deadlines
    deadlines = (
        db.query(Deadline)
        .filter(Deadline.is_completed.is_(False))
        .all()
    )

    dispatched: List[Dict[str, Any]] = []

    for deadline in deadlines:
        due_dt = parse_deadline_due_datetime(deadline.due_date)
        if not due_dt:
            continue

        hours_remaining = (due_dt - now).total_seconds() / 3600.0

        # If deadline has already passed, skip reminders
        if hours_remaining <= 0:
            continue

        threshold_hit: Optional[str] = None
        hours_label = ""

        # Priority 1: 12 Hours Threshold (<= 12 hours)
        if hours_remaining <= 12.0 and not deadline.reminded_12h:
            threshold_hit = "12h"
            hours_label = "12 hours"
            deadline.reminded_12h = True
            deadline.reminded_24h = True
            deadline.reminded_48h = True

        # Priority 2: 24 Hours Threshold (<= 24 hours)
        elif hours_remaining <= 24.0 and not deadline.reminded_24h:
            threshold_hit = "24h"
            hours_label = "24 hours"
            deadline.reminded_24h = True
            deadline.reminded_48h = True

        # Priority 3: 48 Hours Threshold (<= 48 hours)
        elif hours_remaining <= 48.0 and not deadline.reminded_48h:
            threshold_hit = "48h"
            hours_label = "48 hours"
            deadline.reminded_48h = True

        if not threshold_hit:
            continue

        # Look up owning user if assigned
        user = db.query(User).filter(User.id == deadline.user_id).first() if deadline.user_id else None

        # 1. Create in-app Notification for the user
        notif_urgency = "URGENT: " if threshold_hit in ("12h", "24h") else ""
        notif = Notification(
            user_id=deadline.user_id,
            website_id=deadline.website_id,
            type="deadline",
            title=f"{notif_urgency}Deadline '{deadline.title}' due in {hours_label}",
            message=f"Deadline '{deadline.title}' is due on {deadline.due_date} (approx. {hours_label} remaining). Please review any pending submissions.",
            target_url=deadline.source_url or "/deadlines",
            is_read=False,
            created_at=utc_now(),
        )
        db.add(notif)

        # 2. Deliver email if user has verified email and notifications enabled
        email_sent = False
        if user and user.email_verified and user.email_notifications_enabled and user.email:
            try:
                sent, _ = await email_service.send_deadline_reminder_email(
                    recipient_name=user.name,
                    recipient_email=user.email,
                    title=deadline.title,
                    due_date=deadline.due_date,
                    hours_label=hours_label,
                    priority=deadline.priority,
                    category=deadline.category,
                    source_url=deadline.source_url,
                    description=deadline.description,
                )
                email_sent = sent
            except Exception as exc:
                logger.warning(f"Failed to dispatch deadline reminder email to {user.email}: {exc}")

        dispatched.append({
            "deadline_id": deadline.id,
            "title": deadline.title,
            "threshold": threshold_hit,
            "hours_remaining": round(hours_remaining, 2),
            "email_sent": email_sent,
            "user_id": deadline.user_id,
        })

    if dispatched:
        try:
            db.commit()
            logger.info("Dispatched %d deadline reminder(s)", len(dispatched))
        except Exception as exc:
            db.rollback()
            logger.error("Failed to commit deadline reminder flags: %exc", exc)

    return dispatched
