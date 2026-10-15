"""API routes for Deadlines and Dashboard Summaries."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Website, Change, Deadline, Notification, User, utc_now
from ..schemas.schemas import (
    DeadlineCreate,
    DeadlineUpdate,
    DeadlineToggleComplete,
    DeadlineResponse,
    DashboardSummaryResponse,
)
from ..services.deadline_extractor import calculate_deadline_metrics
from ..services import auth_service, email_service, deadline_reminder_service

router = APIRouter(tags=["deadlines"])


@router.get("", response_model=List[DeadlineResponse], summary="List all deadlines")
def get_deadlines(
    is_completed: Optional[bool] = Query(default=None, description="Filter by completion status"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    priority: Optional[str] = Query(default=None, description="Filter by priority"),
    website_id: Optional[int] = Query(default=None, description="Filter by source website ID"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: Optional[User] = Depends(auth_service.get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all deadlines tracked in the SQLite database with optional filters scoped to user."""
    query = db.query(Deadline)
    if current_user:
        query = query.filter(Deadline.user_id == current_user.id)


    if is_completed is not None:
        query = query.filter(Deadline.is_completed.is_(is_completed))
    if category:
        query = query.filter(Deadline.category.ilike(f"%{category.strip()}%"))
    if priority:
        query = query.filter(Deadline.priority == priority.strip().lower())
    if website_id is not None:
        query = query.filter(Deadline.website_id == website_id)

    items = query.order_by(Deadline.due_date.asc()).offset(skip).limit(limit).all()

    # Dynamically keep days_left and status updated based on current calendar date
    has_updates = False
    for item in items:
        days_left, current_status, _ = calculate_deadline_metrics(item.due_date, item.is_completed)
        if item.days_left != days_left or item.status != current_status:
            item.days_left = days_left
            item.status = current_status
            has_updates = True

    if has_updates:
        db.commit()

    return items


@router.get("/summary", response_model=DashboardSummaryResponse, summary="Get dashboard summary metrics")
def get_dashboard_summary(
    current_user: Optional[User] = Depends(auth_service.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Compute real dashboard metric counts directly from SQLite persistent storage."""
    ws_query = db.query(Website)
    dl_query = db.query(Deadline)
    notif_query = db.query(Notification)
    ch_query = db.query(Change).join(Website, Change.website_id == Website.id)

    if current_user:
        ws_query = ws_query.filter(Website.user_id == current_user.id)
        dl_query = dl_query.filter(Deadline.user_id == current_user.id)
        notif_query = notif_query.filter(Notification.user_id == current_user.id)
        ch_query = ch_query.filter(Website.user_id == current_user.id)

    active_count = ws_query.filter(Website.status == "active").count()
    total_changes = ch_query.count()
    upcoming_deadlines = dl_query.filter(Deadline.is_completed.is_(False)).count()
    unread_notifications = notif_query.filter(Notification.is_read.is_(False)).count()

    return {
        "active_monitors_count": active_count,
        "total_changes_detected": total_changes,
        "upcoming_deadlines_count": upcoming_deadlines,
        "unread_notifications_count": unread_notifications,
        "health_status": "Healthy",
    }


@router.post("", response_model=DeadlineResponse, status_code=status.HTTP_201_CREATED, summary="Create a new deadline")
async def create_deadline(
    payload: DeadlineCreate,
    current_user: Optional[User] = Depends(auth_service.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Create and persist a new deadline in SQLite and notify user via email."""
    user_id = current_user.id if current_user else None
    if payload.website_id is not None:
        site_query = db.query(Website).filter(Website.id == payload.website_id)
        if user_id:
            site_query = site_query.filter(Website.user_id == user_id)
        site = site_query.first()
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Associated website with ID {payload.website_id} not found."
            )

    days_left, calculated_status, _ = calculate_deadline_metrics(payload.due_date, is_completed=False)

    deadline = Deadline(
        user_id=user_id,
        website_id=payload.website_id,
        title=payload.title,
        description=payload.description,
        due_date=payload.due_date,
        priority=payload.priority,
        is_completed=False,
        status=calculated_status,
        days_left=days_left,
        category=payload.category or "Academic",
        source_url=payload.source_url,
        reminded_48h=False,
        reminded_24h=False,
        reminded_12h=False,
        created_at=utc_now(),
    )
    db.add(deadline)
    db.commit()
    db.refresh(deadline)

    # Deliver deadline created email if user is verified and enabled email alerts
    if current_user and current_user.email_verified and current_user.email_notifications_enabled and current_user.email:
        try:
            await email_service.send_deadline_created_email(
                recipient_name=current_user.name,
                recipient_email=current_user.email,
                title=deadline.title,
                due_date=deadline.due_date,
                priority=deadline.priority,
                category=deadline.category,
                source_url=deadline.source_url,
                description=deadline.description,
            )
        except Exception:
            # Delivery failure must not abort deadline persistence
            pass

    return deadline


@router.get("/{deadline_id}", response_model=DeadlineResponse, summary="Retrieve a single deadline")
def get_deadline(
    deadline_id: int,
    current_user: Optional[User] = Depends(auth_service.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve an individual deadline by ID."""
    query = db.query(Deadline).filter(Deadline.id == deadline_id)
    if current_user:
        query = query.filter(Deadline.user_id == current_user.id)
    deadline = query.first()
    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deadline with ID {deadline_id} not found."
        )

    days_left, current_status, _ = calculate_deadline_metrics(deadline.due_date, deadline.is_completed)
    if deadline.days_left != days_left or deadline.status != current_status:
        deadline.days_left = days_left
        deadline.status = current_status
        db.commit()
        db.refresh(deadline)

    return deadline


@router.put("/{deadline_id}", response_model=DeadlineResponse, summary="Update an existing deadline")
def update_deadline(
    deadline_id: int,
    payload: DeadlineUpdate,
    current_user: Optional[User] = Depends(auth_service.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Update fields of an existing deadline."""
    query = db.query(Deadline).filter(Deadline.id == deadline_id)
    if current_user:
        query = query.filter(Deadline.user_id == current_user.id)
    deadline = query.first()
    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deadline with ID {deadline_id} not found."
        )

    if payload.website_id is not None:
        site_query = db.query(Website).filter(Website.id == payload.website_id)
        if current_user:
            site_query = site_query.filter(Website.user_id == current_user.id)
        site = site_query.first()
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Associated website with ID {payload.website_id} not found."
            )
        deadline.website_id = payload.website_id

    if payload.title is not None:
        deadline.title = payload.title
    if payload.due_date is not None:
        if payload.due_date != deadline.due_date:
            deadline.due_date = payload.due_date
            deadline.reminded_48h = False
            deadline.reminded_24h = False
            deadline.reminded_12h = False
    if payload.priority is not None:
        deadline.priority = payload.priority
    if payload.category is not None:
        deadline.category = payload.category
    if payload.description is not None:
        deadline.description = payload.description
    if payload.source_url is not None:
        deadline.source_url = payload.source_url
    if payload.is_completed is not None:
        deadline.is_completed = payload.is_completed

    days_left, current_status, _ = calculate_deadline_metrics(deadline.due_date, deadline.is_completed)
    deadline.days_left = days_left
    deadline.status = current_status

    db.commit()
    db.refresh(deadline)
    return deadline


@router.patch("/{deadline_id}/complete", response_model=DeadlineResponse, summary="Toggle or set deadline completion")
def toggle_deadline_completion(
    deadline_id: int,
    payload: Optional[DeadlineToggleComplete] = None,
    current_user: Optional[User] = Depends(auth_service.get_optional_current_user),
    db: Session = Depends(get_db),
):
    """Mark a deadline completed or reopen it."""
    query = db.query(Deadline).filter(Deadline.id == deadline_id)
    if current_user:
        query = query.filter(Deadline.user_id == current_user.id)
    deadline = query.first()
    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deadline with ID {deadline_id} not found."
        )

    if payload and payload.is_completed is not None:
        deadline.is_completed = payload.is_completed
    else:
        deadline.is_completed = not deadline.is_completed

    days_left, current_status, _ = calculate_deadline_metrics(deadline.due_date, deadline.is_completed)
    deadline.days_left = days_left
    deadline.status = current_status

    db.commit()
    db.refresh(deadline)
    return deadline


@router.delete("/{deadline_id}", summary="Delete a deadline")
def delete_deadline(
    deadline_id: int,
    current_user: Optional[User] = Depends(auth_service.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Delete a deadline permanently from SQLite."""
    query = db.query(Deadline).filter(Deadline.id == deadline_id)
    if current_user:
        query = query.filter(Deadline.user_id == current_user.id)
    deadline = query.first()
    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deadline with ID {deadline_id} not found."
        )

    db.delete(deadline)
    db.commit()
    return {"message": f"Deadline {deadline_id} deleted successfully", "id": deadline_id}


@router.post("/check-reminders", summary="Trigger manual evaluation of deadline reminders")
async def check_deadline_reminders(
    current_user: Optional[User] = Depends(auth_service.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Scan and process pending 48h, 24h, and 12h deadline reminders."""
    dispatched = await deadline_reminder_service.process_deadline_reminders(db)
    return {
        "status": "success",
        "reminders_dispatched": len(dispatched),
        "details": dispatched
    }



