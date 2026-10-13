"""API routes for Deadlines and Dashboard Summaries."""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Website, Change, Deadline, Notification
from ..schemas.schemas import DeadlineResponse, DashboardSummaryResponse

router = APIRouter(tags=["deadlines"])


@router.get("", response_model=List[DeadlineResponse], summary="List all deadlines")
def get_deadlines(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Retrieve all deadlines tracked in the SQLite database."""
    return db.query(Deadline).order_by(Deadline.due_date.asc()).offset(skip).limit(limit).all()


@router.get("/summary", response_model=DashboardSummaryResponse, summary="Get dashboard summary metrics")
def get_dashboard_summary(db: Session = Depends(get_db)):
    """Compute real dashboard metric counts directly from SQLite persistent storage."""
    active_count = db.query(Website).filter(Website.status == "active").count()
    total_changes = db.query(Change).count()
    upcoming_deadlines = db.query(Deadline).filter(Deadline.is_completed.is_(False)).count()
    unread_notifications = db.query(Notification).filter(Notification.is_read.is_(False)).count()

    return {
        "active_monitors_count": active_count,
        "total_changes_detected": total_changes,
        "upcoming_deadlines_count": upcoming_deadlines,
        "unread_notifications_count": unread_notifications,
        "health_status": "Healthy"
    }
