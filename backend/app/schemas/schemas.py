"""Pydantic schemas for ChangeRadar request validation and API responses."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class WebsiteBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, description="Friendly title of the monitored page")
    url: str = Field(..., min_length=8, max_length=1024, description="Public HTTP or HTTPS target URL")
    category: Optional[str] = Field(default="General", max_length=100)
    selector: Optional[str] = Field(default=None, max_length=255, description="Optional CSS selector")
    check_interval_minutes: int = Field(default=60, ge=1, le=10080, description="Polling frequency in minutes")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("Website name cannot be blank or whitespace only")
        return trimmed

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        trimmed = v.strip()
        if not (trimmed.startswith("http://") or trimmed.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        if len(trimmed) < 10 or "." not in trimmed:
            raise ValueError("URL must contain a valid domain (e.g., https://example.edu)")
        return trimmed


class WebsiteCreate(WebsiteBase):
    pass


class WebsiteResponse(WebsiteBase):
    id: int
    status: str
    last_checked_at: Optional[datetime] = None
    last_change_at: Optional[datetime] = None
    change_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SnapshotResponse(BaseModel):
    id: int
    website_id: int
    content_hash: str
    captured_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChangeResponse(BaseModel):
    id: int
    website_id: int
    website_name: Optional[str] = None
    previous_snapshot_id: Optional[int] = None
    new_snapshot_id: Optional[int] = None
    detected_at: datetime
    summary: str
    change_type: str = "modification"
    additions_count: int = 0
    deletions_count: int = 0
    old_content_snippet: Optional[str] = None
    new_content_snippet: Optional[str] = None
    is_read: bool = False

    model_config = ConfigDict(from_attributes=True)


class DeadlineResponse(BaseModel):
    id: int
    website_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    due_date: str
    days_left: int = 0
    priority: str = "medium"
    is_completed: bool = False
    status: str = "upcoming"
    category: str = "Academic"
    source_url: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationResponse(BaseModel):
    id: int
    website_id: Optional[int] = None
    change_id: Optional[int] = None
    type: str = "system"
    title: str
    message: str
    is_read: bool = False
    target_url: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardSummaryResponse(BaseModel):
    active_monitors_count: int
    total_changes_detected: int
    upcoming_deadlines_count: int
    unread_notifications_count: int
    health_status: str
