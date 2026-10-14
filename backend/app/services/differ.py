"""Text differ service using Python standard library difflib.

Computes line-level unified differences, categorizes changes (addition, deletion, modification),
and creates human-readable summaries and preview snippets.
"""

import difflib
from typing import Any, Dict


def compute_text_diff(old_text: str, new_text: str) -> Dict[str, Any]:
    """Compare previous and current content using difflib.

    Returns:
        dict containing:
            - has_changes: bool
            - change_type: 'none' | 'addition' | 'deletion' | 'modification'
            - additions_count: int
            - deletions_count: int
            - summary: str
            - unified_diff: str
            - old_content_snippet: str
            - new_content_snippet: str
    """
    if old_text == new_text:
        return {
            "has_changes": False,
            "change_type": "none",
            "additions_count": 0,
            "deletions_count": 0,
            "summary": "No meaningful changes detected.",
            "unified_diff": "",
            "old_content_snippet": "",
            "new_content_snippet": "",
        }

    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    diff_generator = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="previous_snapshot",
        tofile="current_snapshot",
        lineterm=""
    )
    diff_lines = list(diff_generator)

    # Filter out header lines (--- and +++)
    added_lines = [
        line[1:].strip()
        for line in diff_lines
        if line.startswith("+") and not line.startswith("+++")
    ]
    deleted_lines = [
        line[1:].strip()
        for line in diff_lines
        if line.startswith("-") and not line.startswith("---")
    ]

    additions = len(added_lines)
    deletions = len(deleted_lines)

    if additions > 0 and deletions > 0:
        change_type = "modification"
        summary = f"Updated content: {additions} line(s) added, {deletions} line(s) removed"
    elif additions > 0:
        change_type = "addition"
        summary = f"Added content: {additions} new line(s) detected"
    elif deletions > 0:
        change_type = "deletion"
        summary = f"Removed content: {deletions} line(s) removed"
    else:
        change_type = "none"
        summary = "No meaningful line changes detected"

    # Create readable preview snippets (first 5 changed lines, capped at 500 chars)
    old_snippet = "\n".join(deleted_lines[:6])[:500] if deleted_lines else ""
    new_snippet = "\n".join(added_lines[:6])[:500] if added_lines else ""

    return {
        "has_changes": additions > 0 or deletions > 0,
        "change_type": change_type,
        "additions_count": additions,
        "deletions_count": deletions,
        "summary": summary,
        "unified_diff": "\n".join(diff_lines),
        "old_content_snippet": old_snippet,
        "new_content_snippet": new_snippet,
    }
