"""API routes for Change History."""

from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Change
from ..schemas.schemas import ChangeResponse

router = APIRouter(tags=["changes"])


@router.get("", response_model=List[ChangeResponse], summary="List all detected changes")
def get_changes(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Retrieve detected webpage content changes from the database."""
    changes = db.query(Change).order_by(Change.detected_at.desc()).offset(skip).limit(limit).all()
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
            "is_read": c.is_read,
        })
    return results
