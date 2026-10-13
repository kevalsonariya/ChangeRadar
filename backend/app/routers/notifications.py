"""API routes for Notifications."""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Notification
from ..schemas.schemas import NotificationResponse

router = APIRouter(tags=["notifications"])


@router.get("", response_model=List[NotificationResponse], summary="List all notifications")
def get_notifications(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Retrieve notifications stored in the SQLite database."""
    return db.query(Notification).order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()
