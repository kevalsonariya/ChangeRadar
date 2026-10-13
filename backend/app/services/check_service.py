"""Website change check and snapshot orchestration service."""

import hashlib
from typing import Any, Dict
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from ..models.models import Website, Snapshot, Change, Notification, utc_now
from ..services.scraper import fetch_webpage_content
from ..services.differ import compute_text_diff


async def check_website(db: Session, website_id: int) -> Dict[str, Any]:
    """Perform an on-demand check for a monitored website.

    - On first check: captures initial baseline snapshot (no false change recorded).
    - On subsequent checks: calculates SHA-256 hash, runs text diff, and records change if content differs.
    - On failure: updates last_checked_at and status='error' without creating an empty snapshot.
    """
    site = db.query(Website).filter(Website.id == website_id).first()
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Website with ID {website_id} not found."
        )

    # 1. Fetch content safely
    success, clean_text, err_msg = await fetch_webpage_content(site.url, site.selector)

    if not success:
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
            detail=f"Failed to check website '{site.name}': {err_msg}"
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

    # Record notification
    notification = Notification(
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
