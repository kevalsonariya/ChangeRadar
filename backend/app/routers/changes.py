"""API routes for Change History and individual change inspection."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Change, Website, User
from ..schemas.schemas import ChangeResponse
from ..services import auth_service

router = APIRouter(tags=["changes"])


@router.get("", response_model=List[ChangeResponse], summary="List all detected changes")
def get_changes(
    website_id: Optional[int] = Query(None, description="Optional filter by website ID"),
    skip: int = 0,
    limit: int = 50,
    current_user: Optional[User] = Depends(auth_service.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve detected webpage content changes from the database scoped to user."""
    query = db.query(Change).join(Website, Change.website_id == Website.id)
    if current_user:
        query = query.filter(Website.user_id == current_user.id)

    if website_id is not None:
        query = query.filter(Change.website_id == website_id)

    changes = query.order_by(Change.detected_at.desc()).offset(skip).limit(limit).all()
    results = []
    for c in changes:
        results.append({
            "id": c.id,
            "website_id": c.website_id,
            "website_name": c.website.name if c.website else "Unknown Target",
            "previous_snapshot_id": c.previous_snapshot_id,
            "new_snapshot_id": c.new_snapshot_id,
            "detected_at": c.detected_at,
            "summary": c.summary,
            "change_type": c.change_type,
            "additions_count": c.additions_count,
            "deletions_count": c.deletions_count,
            "old_content_snippet": c.old_content_snippet,
            "new_content_snippet": c.new_content_snippet,
            "diff_unified": c.diff_unified,
            "is_read": c.is_read,
        })
    return results


@router.get("/{change_id}", response_model=ChangeResponse, summary="Get details of a specific change")
def get_change_details(
    change_id: int,
    current_user: Optional[User] = Depends(auth_service.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve full details of a specific detected change, including the unified diff."""
    query = db.query(Change).join(Website, Change.website_id == Website.id).filter(Change.id == change_id)
    if current_user:
        query = query.filter(Website.user_id == current_user.id)
    c = query.first()
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change with ID {change_id} not found."
        )

    return {
        "id": c.id,
        "website_id": c.website_id,
        "website_name": c.website.name if c.website else "Unknown Target",
        "previous_snapshot_id": c.previous_snapshot_id,
        "new_snapshot_id": c.new_snapshot_id,
        "detected_at": c.detected_at,
        "summary": c.summary,
        "change_type": c.change_type,
        "additions_count": c.additions_count,
        "deletions_count": c.deletions_count,
        "old_content_snippet": c.old_content_snippet,
        "new_content_snippet": c.new_content_snippet,
        "diff_unified": c.diff_unified,
        "is_read": c.is_read,
    }


@router.patch("/{change_id}/read", response_model=ChangeResponse, summary="Mark change as reviewed/read")
def mark_change_read(
    change_id: int,
    current_user: Optional[User] = Depends(auth_service.get_optional_current_user),
    db: Session = Depends(get_db)
):
    """Mark a detected change as reviewed/read with user scope."""
    query = db.query(Change).join(Website, Change.website_id == Website.id).filter(Change.id == change_id)
    if current_user:
        query = query.filter(Website.user_id == current_user.id)

    c = query.first()
    if not c:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Change with ID {change_id} not found."
        )

    c.is_read = True
    db.commit()
    db.refresh(c)

    return {
        "id": c.id,
        "website_id": c.website_id,
        "website_name": c.website.name if c.website else "Unknown Target",
        "previous_snapshot_id": c.previous_snapshot_id,
        "new_snapshot_id": c.new_snapshot_id,
        "detected_at": c.detected_at,
        "summary": c.summary,
        "change_type": c.change_type,
        "additions_count": c.additions_count,
        "deletions_count": c.deletions_count,
        "old_content_snippet": c.old_content_snippet,
        "new_content_snippet": c.new_content_snippet,
        "diff_unified": c.diff_unified,
        "is_read": c.is_read,
    }

