"""SQLAlchemy models for ChangeRadar SQLite database."""

from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from ..database import Base

class Website(Base):
    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False)
    category = Column(String(100), default="General")
    selector = Column(String(255), nullable=True)  # Optional CSS selector to monitor specific element
    check_interval_minutes = Column(Integer, default=60)
    status = Column(String(50), default="active")  # active, warning, error, paused
    last_checked_at = Column(DateTime, nullable=True)
    last_change_at = Column(DateTime, nullable=True)
    last_content_hash = Column(String(64), nullable=True)
    last_content_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    changes = relationship("ChangeHistory", back_populates="website", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", back_populates="website", cascade="all, delete-orphan")

class ChangeHistory(Base):
    __tablename__ = "change_histories"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=False)
    detected_at = Column(DateTime, default=datetime.utcnow)
    summary = Column(String(500), nullable=False)
    change_type = Column(String(50), default="modification")  # addition, deletion, modification
    additions_count = Column(Integer, default=0)
    deletions_count = Column(Integer, default=0)
    old_content_snippet = Column(Text, nullable=True)
    new_content_snippet = Column(Text, nullable=True)
    diff_unified = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False)

    website = relationship("Website", back_populates="changes")

class Deadline(Base):
    __tablename__ = "deadlines"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id"), nullable=True)
    title = Column(String(255), nullable=False)
    due_date = Column(String(100), nullable=False)  # e.g. "2026-10-25" or parsed string
    days_left = Column(Integer, default=0)
    source_url = Column(String(1024), nullable=False)
    priority = Column(String(50), default="medium")  # high, medium, low
    status = Column(String(50), default="upcoming")  # upcoming, critical, passed
    category = Column(String(100), default="Academic")
    created_at = Column(DateTime, default=datetime.utcnow)

    website = relationship("Website", back_populates="deadlines")

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), default="change")  # change, deadline, system
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(String(100), nullable=False)
    is_read = Column(Boolean, default=False)
    target_url = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
