"""SQLAlchemy models for ChangeRadar SQLite database.

Covers websites, snapshots, content changes, notifications, and deadlines.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from ..database import Base


def utc_now() -> datetime:
    """Helper to return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class User(Base):
    """User account model for authentication and notification preferences."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(512), nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    email_notifications_enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    websites = relationship("Website", back_populates="user", cascade="all, delete-orphan")
    deadlines = relationship("Deadline", back_populates="user", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    verification_tokens = relationship("EmailVerificationToken", back_populates="user", cascade="all, delete-orphan")


class UserSession(Base):
    """Active user session for secure cookie / bearer authentication."""

    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(128), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    user = relationship("User", back_populates="sessions")


class EmailVerificationToken(Base):
    """Expiring single-use token for email verification."""

    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(128), unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="verification_tokens")


class Website(Base):
    """Monitored website configuration and status."""

    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    url = Column(String(1024), nullable=False, unique=True, index=True)
    category = Column(String(100), default="General", nullable=False)
    selector = Column(String(255), nullable=True)  # Optional CSS selector for element targeting
    check_interval_minutes = Column(Integer, default=60, nullable=False)
    render_js = Column(Boolean, default=False, nullable=False)  # Optional client-side JS rendering via headless browser
    status = Column(String(50), default="active", nullable=False)  # active, warning, error, paused
    last_checked_at = Column(DateTime, nullable=True)
    last_change_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="websites")
    snapshots = relationship(
        "Snapshot",
        back_populates="website",
        cascade="all, delete-orphan",
        order_by="desc(Snapshot.captured_at)"
    )
    changes = relationship(
        "Change",
        back_populates="website",
        cascade="all, delete-orphan",
        order_by="desc(Change.detected_at)"
    )
    notifications = relationship(
        "Notification",
        back_populates="website",
        cascade="all, delete-orphan",
        order_by="desc(Notification.created_at)"
    )
    deadlines = relationship(
        "Deadline",
        back_populates="website",
        cascade="all, delete-orphan",
        order_by="Deadline.due_date"
    )


class Snapshot(Base):
    """Raw content snapshot captured during a crawl."""

    __tablename__ = "snapshots"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    content_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash of extracted text
    captured_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    website = relationship("Website", back_populates="snapshots")


class Change(Base):
    """Detected content change between two consecutive snapshots."""

    __tablename__ = "changes"

    id = Column(Integer, primary_key=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_snapshot_id = Column(Integer, ForeignKey("snapshots.id", ondelete="SET NULL"), nullable=True)
    new_snapshot_id = Column(Integer, ForeignKey("snapshots.id", ondelete="SET NULL"), nullable=True)
    detected_at = Column(DateTime, default=utc_now, nullable=False)
    summary = Column(String(500), nullable=False)
    change_type = Column(String(50), default="modification", nullable=False)  # modification, addition, deletion
    additions_count = Column(Integer, default=0, nullable=False)
    deletions_count = Column(Integer, default=0, nullable=False)
    old_content_snippet = Column(Text, nullable=True)
    new_content_snippet = Column(Text, nullable=True)
    diff_unified = Column(Text, nullable=True)
    is_read = Column(Boolean, default=False, nullable=False)

    # Relationships
    website = relationship("Website", back_populates="changes")
    previous_snapshot = relationship("Snapshot", foreign_keys=[previous_snapshot_id])
    new_snapshot = relationship("Snapshot", foreign_keys=[new_snapshot_id])
    notifications = relationship("Notification", back_populates="change", cascade="all, delete-orphan")


class Notification(Base):
    """System and change alert notifications."""

    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id", ondelete="CASCADE"), nullable=True, index=True)
    change_id = Column(Integer, ForeignKey("changes.id", ondelete="CASCADE"), nullable=True, index=True)
    type = Column(String(50), default="system", nullable=False)  # change, deadline, system
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    target_url = Column(String(1024), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="notifications")
    website = relationship("Website", back_populates="notifications")
    change = relationship("Change", back_populates="notifications")


class Deadline(Base):
    """Tracked submission or examination deadline."""

    __tablename__ = "deadlines"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    website_id = Column(Integer, ForeignKey("websites.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    due_date = Column(String(100), nullable=False)  # e.g., '2026-10-25'
    priority = Column(String(50), default="medium", nullable=False)  # high, medium, low
    is_completed = Column(Boolean, default=False, nullable=False)  # completion status
    status = Column(String(50), default="upcoming", nullable=False)  # upcoming, critical, passed
    days_left = Column(Integer, default=0, nullable=False)
    category = Column(String(100), default="Academic", nullable=False)
    source_url = Column(String(1024), nullable=True)
    reminded_48h = Column(Boolean, default=False, nullable=False)
    reminded_24h = Column(Boolean, default=False, nullable=False)
    reminded_12h = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    user = relationship("User", back_populates="deadlines")
    website = relationship("Website", back_populates="deadlines")
