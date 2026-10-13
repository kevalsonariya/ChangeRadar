"""API routes for Notifications."""

from fastapi import APIRouter
from typing import List
from ..schemas.schemas import NotificationResponse

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

_DEMO_NOTIFICATIONS = [
    {
        "id": 1,
        "type": "change",
        "title": "Exam Schedule Updated",
        "message": "GTU Examination Notices updated the practical timetable.",
        "timestamp": "20 minutes ago",
        "is_read": False,
        "target_url": "https://www.gtu.ac.in/Circular.aspx"
    },
    {
        "id": 2,
        "type": "deadline",
        "title": "Deadline Critical: Hackathon Registration",
        "message": "ACM Student Chapter Hackathon registration closes in 3 days.",
        "timestamp": "2 hours ago",
        "is_read": False,
        "target_url": "https://studentevents.college.edu/hackathon"
    },
    {
        "id": 3,
        "type": "system",
        "title": "Hourly Monitor Check Completed",
        "message": "All 4 monitored websites were verified successfully.",
        "timestamp": "3 hours ago",
        "is_read": True,
        "target_url": None
    }
]

@router.get("", response_model=List[NotificationResponse])
def get_notifications():
    return _DEMO_NOTIFICATIONS
