"""API routes for Change History."""

from fastapi import APIRouter
from typing import List
from ..schemas.schemas import ChangeResponse

router = APIRouter(prefix="/api/changes", tags=["changes"])

_DEMO_CHANGES = [
    {
        "id": 101,
        "website_id": 1,
        "website_name": "GTU Examination Notices",
        "detected_at": "2026-10-13T19:40:00",
        "summary": "Updated Winter 2026 Practical Exam Time Table schedule",
        "change_type": "modification",
        "additions_count": 14,
        "deletions_count": 6,
        "old_content_snippet": "B.E. Sem 5 Practical Exam dates will be declared after internal submission by Oct 18.",
        "new_content_snippet": "B.E. Sem 5 Practical Exam finalized: Oct 28 - Nov 05, 2026. Hall tickets available Oct 22.",
        "is_read": False
    },
    {
        "id": 102,
        "website_id": 2,
        "website_name": "NPTEL Assignment Submission Portal",
        "detected_at": "2026-10-12T16:20:00",
        "summary": "Assignment 8 Deadline extended by 4 days",
        "change_type": "addition",
        "additions_count": 8,
        "deletions_count": 2,
        "old_content_snippet": "Week 8 assignment due date: Oct 14, 2026 23:59 IST.",
        "new_content_snippet": "NOTICE: Week 8 assignment due date extended to Oct 18, 2026 23:59 IST due to server maintenance.",
        "is_read": True
    },
    {
        "id": 103,
        "website_id": 3,
        "website_name": "ACM Student Chapter Hackathon Page",
        "detected_at": "2026-10-11T14:10:00",
        "summary": "Added problem statement tracks for AI/ML & Web3 and increased prize pool",
        "change_type": "modification",
        "additions_count": 22,
        "deletions_count": 4,
        "old_content_snippet": "Hackathon tracks will be announced on Oct 15.",
        "new_content_snippet": "Tracks live: 1. AI Assistant tooling 2. Campus productivity 3. Open Innovation. Grand Prize: 50,000 INR.",
        "is_read": True
    }
]

@router.get("", response_model=List[ChangeResponse])
def get_changes():
    return _DEMO_CHANGES
