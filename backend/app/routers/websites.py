"""API routes for Monitored Websites CRUD operations and on-demand checking."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..database import get_db
from ..models.models import Change
from ..schemas.schemas import WebsiteCreate, WebsiteResponse, CheckWebsiteResponse, ChangeResponse
from ..services import website_service, check_service

router = APIRouter(tags=["websites"])


@router.get("", response_model=List[WebsiteResponse], summary="List all monitored websites")
def list_websites(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Retrieve all websites currently registered for monitoring."""
    websites = website_service.get_all_websites(db, skip=skip, limit=limit)
    response_list = []
    for site in websites:
        site_dict = {
            "id": site.id,
            "name": site.name,
            "url": site.url,
            "category": site.category,
            "selector": site.selector,
            "check_interval_minutes": site.check_interval_minutes,
            "status": site.status,
            "last_checked_at": site.last_checked_at,
            "last_change_at": site.last_change_at,
            "change_count": len(site.changes) if site.changes else 0,
            "created_at": site.created_at,
        }
        response_list.append(site_dict)
    return response_list


@router.post(
    "",
    response_model=WebsiteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new website to monitor"
)
def create_website(
    website_in: WebsiteCreate,
    db: Session = Depends(get_db)
):
    """Register a new public webpage for change monitoring."""
    # Check for duplicate URL
    existing = website_service.get_website_by_url(db, website_in.url)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Website with URL '{website_in.url}' is already registered (ID: {existing.id})"
        )

    new_site = website_service.create_website(db, website_in)
    return {
        "id": new_site.id,
        "name": new_site.name,
        "url": new_site.url,
        "category": new_site.category,
        "selector": new_site.selector,
        "check_interval_minutes": new_site.check_interval_minutes,
        "status": new_site.status,
        "last_checked_at": new_site.last_checked_at,
        "last_change_at": new_site.last_change_at,
        "change_count": 0,
        "created_at": new_site.created_at,
    }


@router.get(
    "/{website_id}",
    response_model=WebsiteResponse,
    summary="Get details for a specific monitored website"
)
def get_website(
    website_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve details for a single monitored website by ID."""
    site = website_service.get_website_by_id(db, website_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Website with ID {website_id} not found"
        )
    return {
        "id": site.id,
        "name": site.name,
        "url": site.url,
        "category": site.category,
        "selector": site.selector,
        "check_interval_minutes": site.check_interval_minutes,
        "status": site.status,
        "last_checked_at": site.last_checked_at,
        "last_change_at": site.last_change_at,
        "change_count": len(site.changes) if site.changes else 0,
        "created_at": site.created_at,
    }


@router.delete(
    "/{website_id}",
    status_code=status.HTTP_200_OK,
    summary="Remove a website from monitoring"
)
def delete_website(
    website_id: int,
    db: Session = Depends(get_db)
):
    """Delete a monitored website and its related history and snapshots."""
    deleted = website_service.delete_website(db, website_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Website with ID {website_id} not found"
        )
    return {
        "message": f"Website with ID {website_id} deleted successfully",
        "id": website_id,
        "status": "deleted"
    }


@router.post(
    "/{website_id}/check",
    response_model=CheckWebsiteResponse,
    summary="Check a website on-demand for content updates"
)
async def check_website_on_demand(
    website_id: int,
    db: Session = Depends(get_db)
):
    """Crawl the website, compare against previous snapshot, and detect changes."""
    return await check_service.check_website(db, website_id)


@router.get(
    "/{website_id}/changes",
    response_model=List[ChangeResponse],
    summary="Get all detected changes for a specific website"
)
def get_website_changes(
    website_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db)
):
    """Retrieve history of content changes for a specific website."""
    site = website_service.get_website_by_id(db, website_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Website with ID {website_id} not found"
        )

    changes = (
        db.query(Change)
        .filter(Change.website_id == website_id)
        .order_by(Change.detected_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    results = []
    for c in changes:
        results.append({
            "id": c.id,
            "website_id": c.website_id,
            "website_name": site.name,
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
