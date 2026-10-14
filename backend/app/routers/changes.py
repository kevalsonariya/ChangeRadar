"""API routes for Change History and individual change inspection."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Change
from ..schemas.schemas import ChangeResponse

router = APIRouter(tags=["changes"])


@router.get("", response_model=List[ChangeResponse], summary="List all detected changes")
def get_changes(
    website_id: Optional[int] = Query(None, description="Optional filter by website ID"),
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Retrieve detected webpage content changes from the database."""
    query = db.query(Change)
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
    db: Session = Depends(get_db)
):
    """Retrieve full details of a specific detected change, including the unified diff."""
    c = db.query(Change).filter(Change.id == change_id).first()
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
    db: Session = Depends(get_db)
):
    """Mark a detected change as reviewed/read."""
    c = db.query(Change).filter(Change.id == change_id).first()
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
