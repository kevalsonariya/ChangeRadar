"""API routes for Monitored Websites."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..schemas.schemas import WebsiteResponse, WebsiteCreate

router = APIRouter(prefix="/api/websites", tags=["websites"])

# Temporary in-memory state until DB migrations run
_DEMO_WEBSITES = [
    {
        "id": 1,
        "name": "GTU Examination Notices",
        "url": "https://www.gtu.ac.in/Circular.aspx",
        "category": "University",
        "selector": ".circular-list",
        "check_interval_minutes": 30,
        "status": "active",
        "last_checked_at": "2026-10-13T21:15:00",
        "last_change_at": "2026-10-13T19:40:00",
        "change_count": 8,
        "created_at": "2026-10-01T10:00:00"
    },
    {
        "id": 2,
        "name": "NPTEL Assignment Submission Portal",
        "url": "https://swayam.gov.in/nc_details/NPTEL",
        "category": "Academics",
        "selector": "#timeline-announcements",
        "check_interval_minutes": 60,
        "status": "active",
        "last_checked_at": "2026-10-13T21:00:00",
        "last_change_at": "2026-10-12T16:20:00",
        "change_count": 3,
        "created_at": "2026-10-02T11:00:00"
    },
    {
        "id": 3,
        "name": "ACM Student Chapter Hackathon Page",
        "url": "https://studentevents.college.edu/hackathon",
        "category": "Competitions",
        "selector": ".announcement-card",
        "check_interval_minutes": 120,
        "status": "warning",
        "last_checked_at": "2026-10-13T20:45:00",
        "last_change_at": "2026-10-11T14:10:00",
        "change_count": 5,
        "created_at": "2026-10-05T09:30:00"
    },
    {
        "id": 4,
        "name": "College Scholarship & Grant Portal",
        "url": "https://scholarships.gov.in",
        "category": "Financial Aid",
        "selector": "#scholarship-deadlines",
        "check_interval_minutes": 240,
        "status": "active",
        "last_checked_at": "2026-10-13T20:00:00",
        "last_change_at": "2026-10-10T12:00:00",
        "change_count": 2,
        "created_at": "2026-10-06T14:15:00"
    }
]

@router.get("", response_model=List[WebsiteResponse])
def get_websites():
    return _DEMO_WEBSITES

@router.post("", response_model=WebsiteResponse)
def create_website(website: WebsiteCreate):
    new_site = {
        "id": len(_DEMO_WEBSITES) + 1,
        "name": website.name,
        "url": website.url,
        "category": website.category or "General",
        "selector": website.selector,
        "check_interval_minutes": website.check_interval_minutes,
        "status": "active",
        "last_checked_at": "2026-10-13T21:30:00",
        "last_change_at": None,
        "change_count": 0,
        "created_at": "2026-10-13T21:30:00"
    }
    _DEMO_WEBSITES.append(new_site)
    return new_site

@router.delete("/{website_id}")
def delete_website(website_id: int):
    global _DEMO_WEBSITES
    _DEMO_WEBSITES = [w for w in _DEMO_WEBSITES if w["id"] != website_id]
    return {"status": "deleted", "id": website_id}
