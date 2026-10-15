"""Website change check and snapshot orchestration service."""

import hashlib
from typing import Any, Dict
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from ..models.models import Website, Snapshot, Change, Notification, utc_now
from ..services.scraper import fetch_webpage_content
from ..services.differ import compute_text_diff
from ..services.deadline_extractor import extract_deadlines_from_text, sync_extracted_deadlines


# Global in-process registry to prevent overlapping checks for the same website
ACTIVE_CHECKS: Set[int] = set()


async def check_website(db: Session, website_id: int, render_js: Optional[bool] = None) -> Dict[str, Any]:
    """Perform a check for a monitored website with in-process concurrency guard."""
    if website_id in ACTIVE_CHECKS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A check for website ID {website_id} is already in progress."
        )

    ACTIVE_CHECKS.add(website_id)
    try:
        return await _check_website_internal(db, website_id, render_js=render_js)
    finally:
        ACTIVE_CHECKS.discard(website_id)


async def _check_website_internal(db: Session, website_id: int, render_js: Optional[bool] = None) -> Dict[str, Any]:
    """Internal implementation of check_website.

    - On first check: captures initial baseline snapshot (no false change recorded).
    - On subsequent checks: calculates SHA-256 hash, runs text diff, and records change if content differs.
    - On failure: updates last_checked_at and status='error' without creating an empty snapshot.
    - Uses short transactions: releases read transaction before network I/O.
    """
    site = db.query(Website).filter(Website.id == website_id).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Website with ID {website_id} not found."
        )

    url = site.url
    selector = site.selector
    name = site.name
    use_render_js = render_js if render_js is not None else getattr(site, "render_js", False)
    db.commit()  # Release read transaction before network request

    # 1. Fetch content safely without holding database locks
    if use_render_js:
        success, clean_text, err_msg = await fetch_webpage_content(url, selector, render_js=True)
    else:
        success, clean_text, err_msg = await fetch_webpage_content(url, selector)

    if not success:
        site = db.query(Website).filter(Website.id == website_id).first()
        if site:
            site.last_checked_at = utc_now()
            site.status = "error"
            db.commit()

        # Differentiate client error (SSRF, bad URL) vs remote server failure
        if "SSRF" in err_msg or "Invalid URL" in err_msg or "Unsupported" in err_msg:
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            status_code = status.HTTP_502_BAD_GATEWAY

        raise HTTPException(
            status_code=status_code,
            detail=f"Failed to check website '{name}': {err_msg}"
        )

    # 2. Compute content hash
    content_hash = hashlib.sha256(clean_text.encode("utf-8")).hexdigest()

    # 3. Retrieve most recent previous snapshot
    previous_snapshot = (
        db.query(Snapshot)
        .filter(Snapshot.website_id == site.id)
        .order_by(Snapshot.captured_at.desc())
        .first()
    )

    checked_time = utc_now()
    site.last_checked_at = checked_time
    site.status = "active"

    # Case A: Initial Baseline Snapshot (Requirement 4)
    if not previous_snapshot:
        baseline = Snapshot(
            website_id=site.id,
            content=clean_text,
            content_hash=content_hash,
            captured_at=checked_time,
        )
        db.add(baseline)
        db.commit()
        db.refresh(baseline)

        # Extract initial deadlines if explicitly present in webpage text
        extracted_deadlines = extract_deadlines_from_text(clean_text)
        if extracted_deadlines:
            new_deadlines = sync_extracted_deadlines(
                db=db,
                extracted_items=extracted_deadlines,
                website_id=site.id,
                source_url=site.url,
                category=site.category or "Academic"
            )
            if site.user and site.user.email_verified and site.user.email_notifications_enabled:
                from . import email_service
                for dl in new_deadlines:
                    try:
                        await email_service.send_deadline_created_email(
                            recipient_name=site.user.name,
                            recipient_email=site.user.email,
                            title=dl.title,
                            due_date=dl.due_date,
                            priority=dl.priority,
                            category=dl.category,
                            source_url=dl.source_url,
                            description=dl.description,
                        )
                    except Exception:
                        pass

        return {
            "website_id": site.id,
            "status": "baseline_created",
            "message": "Baseline snapshot captured. Subsequent checks will monitor for changes.",
            "snapshot_id": baseline.id,
            "change_id": None,
            "content_hash": content_hash,
            "detected_change": None,
            "checked_at": checked_time,
        }

    # Case B: Subsequent Check — Unchanged Content (Requirement 5)
    if previous_snapshot.content_hash == content_hash or previous_snapshot.content == clean_text:
        db.commit()
        return {
            "website_id": site.id,
            "status": "no_change",
            "message": "No meaningful changes detected since the last snapshot.",
            "snapshot_id": previous_snapshot.id,
            "change_id": None,
            "content_hash": content_hash,
            "detected_change": None,
            "checked_at": checked_time,
        }

    # Case C: Subsequent Check — Meaningful Content Change Detected (Requirement 5 & 6)
    diff_data = compute_text_diff(previous_snapshot.content, clean_text)

    if not diff_data["has_changes"]:
        db.commit()
        return {
            "website_id": site.id,
            "status": "no_change",
            "message": "No meaningful line changes detected.",
            "snapshot_id": previous_snapshot.id,
            "change_id": None,
            "content_hash": content_hash,
            "detected_change": None,
            "checked_at": checked_time,
        }

    # Save new snapshot
    new_snapshot = Snapshot(
        website_id=site.id,
        content=clean_text,
        content_hash=content_hash,
        captured_at=checked_time,
    )
    db.add(new_snapshot)
    db.flush()

    # Save change record
    change_record = Change(
        website_id=site.id,
        previous_snapshot_id=previous_snapshot.id,
        new_snapshot_id=new_snapshot.id,
        detected_at=checked_time,
        summary=diff_data["summary"],
        change_type=diff_data["change_type"],
        additions_count=diff_data["additions_count"],
        deletions_count=diff_data["deletions_count"],
        old_content_snippet=diff_data["old_content_snippet"],
        new_content_snippet=diff_data["new_content_snippet"],
        diff_unified=diff_data["unified_diff"],
        is_read=False,
    )
    db.add(change_record)
    db.flush()

    # Record in-app notification
    notification = Notification(
        user_id=site.user_id,
        website_id=site.id,
        change_id=change_record.id,
        type="change",
        title=f"Change Detected: {site.name}",
        message=diff_data["summary"],
        is_read=False,
        target_url=site.url,
        created_at=checked_time,
    )
    db.add(notification)

    # Update website last change timestamp
    site.last_change_at = checked_time
    db.commit()

    # User-specific Email Delivery (Requirement 5)
    # Check if the website has an owning user with verified email and email alerts enabled
    if site.user_id and site.user:
        owner = site.user
        if owner.email_verified and owner.email_notifications_enabled:
            from . import email_service
            try:
                await email_service.send_change_alert_email(
                    recipient_name=owner.name,
                    recipient_email=owner.email,
                    website_name=site.name,
                    website_url=site.url,
                    summary=diff_data["summary"],
                    additions_count=diff_data["additions_count"],
                    deletions_count=diff_data["deletions_count"],
                    change_type=diff_data["change_type"]
                )
            except Exception as email_err:
                # Delivery failure must not undo monitoring check or database persistence
                pass

    # Extract deadlines from updated content if present
    extracted_deadlines = extract_deadlines_from_text(clean_text)
    if extracted_deadlines:
        new_deadlines = sync_extracted_deadlines(
            db=db,
            extracted_items=extracted_deadlines,
            website_id=site.id,
            source_url=site.url,
            category=site.category or "Academic"
        )
        if site.user and site.user.email_verified and site.user.email_notifications_enabled:
            from . import email_service
            for dl in new_deadlines:
                try:
                    await email_service.send_deadline_created_email(
                        recipient_name=site.user.name,
                        recipient_email=site.user.email,
                        title=dl.title,
                        due_date=dl.due_date,
                        priority=dl.priority,
                        category=dl.category,
                        source_url=dl.source_url,
                        description=dl.description,
                    )
                except Exception:
                    pass


    return {
        "website_id": site.id,
        "status": "change_detected",
        "message": diff_data["summary"],
        "snapshot_id": new_snapshot.id,
        "change_id": change_record.id,
        "content_hash": content_hash,
        "detected_change": {
            "id": change_record.id,
            "website_id": site.id,
            "website_name": site.name,
            "detected_at": change_record.detected_at,
            "summary": change_record.summary,
            "change_type": change_record.change_type,
            "additions_count": change_record.additions_count,
            "deletions_count": change_record.deletions_count,
            "old_content_snippet": change_record.old_content_snippet,
            "new_content_snippet": change_record.new_content_snippet,
            "diff_unified": change_record.diff_unified,
            "is_read": change_record.is_read,
        },
        "checked_at": checked_time,
    }
