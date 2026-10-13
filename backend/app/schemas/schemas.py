"""Pydantic schemas for ChangeRadar API endpoints."""

from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime

class WebsiteBase(BaseModel):
    name: str
    url: str
    category: Optional[str] = "General"
    selector: Optional[str] = None
    check_interval_minutes: int = 60

class WebsiteCreate(WebsiteBase):
    pass

class WebsiteResponse(WebsiteBase):
    id: int
    status: str
    last_checked_at: Optional[datetime] = None
    last_change_at: Optional[datetime] = None
    change_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True

class ChangeResponse(BaseModel):
    id: int
    website_id: int
    website_name: str
    detected_at: datetime
    summary: str
    change_type: str  # modification, addition, deletion
    additions_count: int
    deletions_count: int
    old_content_snippet: Optional[str] = None
    new_content_snippet: Optional[str] = None
    is_read: bool = False

    class Config:
        from_attributes = True

class DeadlineResponse(BaseModel):
    id: int
    website_id: Optional[int] = None
    title: str
    due_date: str
    days_left: int
    source_url: str
    priority: str  # high, medium, low
    status: str    # upcoming, critical, passed
    category: str

    class Config:
        from_attributes = True

class NotificationResponse(BaseModel):
    id: int
    type: str  # change, deadline, system
    title: str
    message: str
    timestamp: str
    is_read: bool
    target_url: Optional[str] = None

    class Config:
        from_attributes = True

class DashboardSummaryResponse(BaseModel):
    active_monitors_count: int
    total_changes_detected: int
    upcoming_deadlines_count: int
    unread_notifications_count: int
    health_status: str
