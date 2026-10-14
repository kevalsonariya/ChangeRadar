"""Database service layer for Website CRUD operations."""

from typing import List, Optional
from sqlalchemy.orm import Session
from ..models.models import Website
from ..schemas.schemas import WebsiteCreate


def get_all_websites(db: Session, skip: int = 0, limit: int = 100) -> List[Website]:
    """Retrieve all monitored websites ordered by creation date (newest first)."""
    return db.query(Website).order_by(Website.created_at.desc()).offset(skip).limit(limit).all()


def get_website_by_id(db: Session, website_id: int) -> Optional[Website]:
    """Retrieve a single monitored website by its database ID."""
    return db.query(Website).filter(Website.id == website_id).first()


def get_website_by_url(db: Session, url: str) -> Optional[Website]:
    """Retrieve a monitored website by exact URL (used for uniqueness checks)."""
    return db.query(Website).filter(Website.url == url.strip()).first()


def create_website(db: Session, website_in: WebsiteCreate) -> Website:
    """Create a new monitored website entry in the database."""
    db_website = Website(
        name=website_in.name,
        url=website_in.url,
        category=website_in.category or "General",
        selector=website_in.selector,
        check_interval_minutes=website_in.check_interval_minutes,
        render_js=getattr(website_in, "render_js", False),
        status="active",
        last_checked_at=None,
        last_change_at=None,
    )
    db.add(db_website)
    db.commit()
    db.refresh(db_website)
    return db_website


def delete_website(db: Session, website_id: int) -> bool:
    """Delete a monitored website by ID. Returns True if deleted, False if not found."""
    db_website = get_website_by_id(db, website_id)
    if not db_website:
        return False
    db.delete(db_website)
    db.commit()
    return True
