"""Automated deadline extraction service for ChangeRadar.

Identifies unambiguous dates associated with deadline keywords in webpage text,
normalizes dates, and inserts non-duplicate Deadlines into SQLite.
"""

import re
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from ..models.models import Deadline, Website, utc_now

# Explicit deadline context keywords
DEADLINE_KEYWORDS = [
    r"deadline",
    r"last\s+date",
    r"due\s+date",
    r"submission\s+date",
    r"cutoff\s+date",
    r"closing\s+date",
    r"final\s+date",
    r"exam\s+date",
]

DEADLINE_KEYWORD_PATTERN = re.compile(
    r"\b(" + "|".join(DEADLINE_KEYWORDS) + r")\b",
    re.IGNORECASE
)

# Unambiguous date regex patterns
DATE_PATTERNS = [
    # Format: Oct 25, 2026 or October 25, 2026
    re.compile(
        r"\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4}\b",
        re.IGNORECASE
    ),
    # Format: 25 Oct 2026 or 25 October 2026
    re.compile(
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?),?\s+\d{4}\b",
        re.IGNORECASE
    ),
    # Format: YYYY-MM-DD
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    # Format: DD/MM/YYYY or DD-MM-YYYY
    re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b"),
]


def normalize_date_string(raw_date: str) -> Optional[str]:
    """Parse raw date string and normalize to standard YYYY-MM-DD format."""
    clean = re.sub(r"(st|nd|rd|th)", "", raw_date).strip()
    formats = [
        "%b %d, %Y",
        "%B %d, %Y",
        "%b %d %Y",
        "%B %d %Y",
        "%d %b %Y",
        "%d %B %Y",
        "%d %b, %Y",
        "%d %B, %Y",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(clean, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def calculate_deadline_metrics(due_date_str: str, is_completed: bool = False):
    """Compute days_left, urgency status, and priority from a due date."""
    today = datetime.now(timezone.utc).date()
    days_left = 7
    status = "upcoming"
    priority = "medium"

    # Try ISO YYYY-MM-DD first, then fallback formats
    parsed_date = None
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            parsed_date = datetime.strptime(due_date_str.strip(), fmt).date()
            break
        except ValueError:
            continue

    if parsed_date:
        delta = (parsed_date - today).days
        days_left = max(0, delta)
        if is_completed:
            status = "completed"
            priority = "low"
        elif delta < 0:
            status = "passed"
            priority = "low"
        elif delta <= 3:
            status = "critical"
            priority = "high"
        elif delta <= 7:
            status = "upcoming"
            priority = "medium"
        else:
            status = "upcoming"
            priority = "low"
    elif is_completed:
        status = "completed"

    return days_left, status, priority


def extract_deadlines_from_text(text: str) -> List[Dict[str, Any]]:
    """Scan cleaned webpage text for explicit deadline phrases with valid dates.

    Requires BOTH a deadline keyword and a parsable date in the same or adjacent line.
    """
    results: List[Dict[str, Any]] = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for idx, line in enumerate(lines):
        # Must contain a deadline keyword
        if not DEADLINE_KEYWORD_PATTERN.search(line):
            continue

        # Look for date in current line first, then adjacent line
        found_date_str = None
        for pattern in DATE_PATTERNS:
            match = pattern.search(line)
            if match:
                found_date_str = match.group(0)
                break

        # Check next line if current line only had the label (e.g. "Submission Deadline:\nOct 25, 2026")
        if not found_date_str and idx + 1 < len(lines):
            next_line = lines[idx + 1]
            for pattern in DATE_PATTERNS:
                match = pattern.search(next_line)
                if match:
                    found_date_str = match.group(0)
                    break

        if not found_date_str:
            continue

        normalized_due_date = normalize_date_string(found_date_str)
        if not normalized_due_date:
            continue

        # Derive title: clean line, truncate to 120 chars
        title = re.sub(r"[\s\:\-]+", " ", line).strip()
        if len(title) > 120:
            title = title[:117] + "..."

        results.append({
            "title": title,
            "description": f"Extracted announcement: \"{line}\"",
            "due_date": normalized_due_date,
            "raw_date": found_date_str,
        })

    return results


def sync_extracted_deadlines(
    db: Session,
    extracted_items: List[Dict[str, Any]],
    website_id: int,
    source_url: Optional[str] = None,
    category: str = "Academic"
) -> List[Deadline]:
    """Insert newly detected deadlines into SQLite without creating duplicates."""
    created_deadlines: List[Deadline] = []
    site = db.query(Website).filter(Website.id == website_id).first()
    owner_user_id = site.user_id if site else None

    for item in extracted_items:
        # Deduplication check: same website, title, and due_date
        existing = (
            db.query(Deadline)
            .filter(
                Deadline.website_id == website_id,
                Deadline.title == item["title"],
                Deadline.due_date == item["due_date"]
            )
            .first()
        )
        if existing:
            continue

        days_left, status, priority = calculate_deadline_metrics(item["due_date"])

        deadline = Deadline(
            user_id=owner_user_id,
            website_id=website_id,
            title=item["title"],
            description=item.get("description"),
            due_date=item["due_date"],
            priority=priority,
            is_completed=False,
            status=status,
            days_left=days_left,
            category=category,
            source_url=source_url,
            reminded_48h=False,
            reminded_24h=False,
            reminded_12h=False,
            created_at=utc_now()
        )
        db.add(deadline)
        created_deadlines.append(deadline)

    if created_deadlines:
        db.commit()
        for d in created_deadlines:
            db.refresh(d)

    return created_deadlines
