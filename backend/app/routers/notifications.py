"""API routes for Notifications."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Notification
from ..schemas.schemas import NotificationResponse

router = APIRouter(tags=["notifications"])


@router.get("", response_model=List[NotificationResponse], summary="List all notifications")
def get_notifications(
    is_read: Optional[bool] = Query(default=None, description="Filter by read status"),
    notification_type: Optional[str] = Query(default=None, alias="type", description="Filter by notification type"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Retrieve notifications stored in the SQLite database."""
    query = db.query(Notification)

    if is_read is not None:
        query = query.filter(Notification.is_read.is_(is_read))
    if notification_type:
        query = query.filter(Notification.type == notification_type.strip().lower())

    return query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()


@router.patch("/{notification_id}/read", response_model=NotificationResponse, summary="Mark single notification as read")
def mark_notification_read(notification_id: int, db: Session = Depends(get_db)):
    """Mark an individual notification as read."""
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification with ID {notification_id} not found."
        )

    notif.is_read = True
    db.commit()
    db.refresh(notif)
    return notif


@router.post("/read-all", summary="Mark all notifications as read")
def mark_all_notifications_read(db: Session = Depends(get_db)):
    """Mark all unread notifications as read across the entire system."""
    updated_count = (
        db.query(Notification)
        .filter(Notification.is_read.is_(False))
        .update({"is_read": True}, synchronize_session=False)
    )
    db.commit()
    return {
        "message": "All notifications marked as read",
        "updated_count": updated_count
    }


@router.delete("/{notification_id}", summary="Delete a notification")
def delete_notification(notification_id: int, db: Session = Depends(get_db)):
    """Delete a single notification from SQLite."""
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification with ID {notification_id} not found."
        )

    db.delete(notif)
    db.commit()
    return {"message": f"Notification {notification_id} deleted successfully", "id": notification_id}
