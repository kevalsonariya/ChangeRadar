"""Diffing service using Python's standard library difflib."""

import difflib
from typing import Dict, Any, List

def compute_text_diff(old_text: str, new_text: str) -> Dict[str, Any]:
    """
    Compare old and new text versions using difflib.
    Returns summary stats, unified diff text, and detected changes.
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="previous_version",
        tofile="current_version",
        lineterm=""
    ))

    additions = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    deletions = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

    if additions > 0 and deletions > 0:
        change_type = "modification"
    elif additions > 0:
        change_type = "addition"
    elif deletions > 0:
        change_type = "deletion"
    else:
        change_type = "none"

    return {
        "has_changes": additions > 0 or deletions > 0,
        "change_type": change_type,
        "additions_count": additions,
        "deletions_count": deletions,
        "unified_diff": "\n".join(diff),
        "summary": f"{additions} lines added, {deletions} lines removed"
    }
