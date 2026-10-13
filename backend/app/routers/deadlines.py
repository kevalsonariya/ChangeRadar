"""API routes for Deadlines and Dashboard Summaries."""

from fastapi import APIRouter
from typing import List
from ..schemas.schemas import DeadlineResponse, DashboardSummaryResponse

router = APIRouter(prefix="/api/deadlines", tags=["deadlines"])

_DEMO_DEADLINES = [
    {
        "id": 1,
        "website_id": 1,
        "title": "GTU Hall Ticket Verification & Download",
        "due_date": "2026-10-22",
        "days_left": 9,
        "source_url": "https://www.gtu.ac.in/Circular.aspx",
        "priority": "high",
        "status": "upcoming",
        "category": "Exams"
    },
    {
        "id": 2,
        "website_id": 2,
        "title": "NPTEL Week 8 Assignment Submission",
        "due_date": "2026-10-18",
        "days_left": 5,
        "source_url": "https://swayam.gov.in/nc_details/NPTEL",
        "priority": "high",
        "status": "upcoming",
        "category": "Assignments"
    },
    {
        "id": 3,
        "website_id": 4,
        "title": "National Scholarship Scheme (NSP) Portal Closes",
        "due_date": "2026-10-31",
        "days_left": 18,
        "source_url": "https://scholarships.gov.in",
        "priority": "medium",
        "status": "upcoming",
        "category": "Scholarships"
    },
    {
        "id": 4,
        "website_id": 3,
        "title": "Hackathon Team Registration Deadline",
        "due_date": "2026-10-16",
        "days_left": 3,
        "source_url": "https://studentevents.college.edu/hackathon",
        "priority": "high",
        "status": "critical",
        "category": "Competitions"
    }
]

@router.get("", response_model=List[DeadlineResponse])
def get_deadlines():
    return _DEMO_DEADLINES

@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary():
    return {
        "active_monitors_count": 4,
        "total_changes_detected": 16,
        "upcoming_deadlines_count": 4,
        "unread_notifications_count": 2,
        "health_status": "Healthy"
    }
