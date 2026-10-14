"""API routes for Deadlines and Dashboard Summaries."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Website, Change, Deadline, Notification, utc_now
from ..schemas.schemas import (
    DeadlineCreate,
    DeadlineUpdate,
    DeadlineToggleComplete,
    DeadlineResponse,
    DashboardSummaryResponse,
)
from ..services.deadline_extractor import calculate_deadline_metrics

router = APIRouter(tags=["deadlines"])


@router.get("", response_model=List[DeadlineResponse], summary="List all deadlines")
def get_deadlines(
    is_completed: Optional[bool] = Query(default=None, description="Filter by completion status"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    priority: Optional[str] = Query(default=None, description="Filter by priority"),
    website_id: Optional[int] = Query(default=None, description="Filter by source website ID"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Retrieve all deadlines tracked in the SQLite database with optional filters."""
    query = db.query(Deadline)

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
        "health_status": "Healthy",
    }


@router.post("", response_model=DeadlineResponse, status_code=status.HTTP_201_CREATED, summary="Create a new deadline")
def create_deadline(payload: DeadlineCreate, db: Session = Depends(get_db)):
    """Create and persist a new deadline in SQLite."""
    if payload.website_id is not None:
        site = db.query(Website).filter(Website.id == payload.website_id).first()
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Associated website with ID {payload.website_id} not found."
            )

    days_left, calculated_status, _ = calculate_deadline_metrics(payload.due_date, is_completed=False)

    deadline = Deadline(
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
        created_at=utc_now(),
    )
    db.add(deadline)
    db.commit()
    db.refresh(deadline)
    return deadline


@router.get("/{deadline_id}", response_model=DeadlineResponse, summary="Retrieve a single deadline")
def get_deadline(deadline_id: int, db: Session = Depends(get_db)):
    """Retrieve an individual deadline by ID."""
    deadline = db.query(Deadline).filter(Deadline.id == deadline_id).first()
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
def update_deadline(deadline_id: int, payload: DeadlineUpdate, db: Session = Depends(get_db)):
    """Update fields of an existing deadline."""
    deadline = db.query(Deadline).filter(Deadline.id == deadline_id).first()
    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deadline with ID {deadline_id} not found."
        )

    if payload.website_id is not None:
        site = db.query(Website).filter(Website.id == payload.website_id).first()
        if not site:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Associated website with ID {payload.website_id} not found."
            )
        deadline.website_id = payload.website_id

    if payload.title is not None:
        deadline.title = payload.title
    if payload.due_date is not None:
        deadline.due_date = payload.due_date
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
    db: Session = Depends(get_db),
):
    """Mark a deadline completed or reopen it."""
    deadline = db.query(Deadline).filter(Deadline.id == deadline_id).first()
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
def delete_deadline(deadline_id: int, db: Session = Depends(get_db)):
    """Delete a deadline permanently from SQLite."""
    deadline = db.query(Deadline).filter(Deadline.id == deadline_id).first()
    if not deadline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Deadline with ID {deadline_id} not found."
        )

    db.delete(deadline)
    db.commit()
    return {"message": f"Deadline {deadline_id} deleted successfully", "id": deadline_id}
