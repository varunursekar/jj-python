"""JSON template strings and parsers for jj output."""

from __future__ import annotations

import json

from .models import Change

# Template that produces valid JSON per change by wrapping json(self) as "base"
# and appending extra fields not included in json(self).
CHANGE_TEMPLATE = (
    'surround("{", "}", '
    '"\\\"base\\\":" ++ json(self)'
    ' ++ ",\\\"bookmarks\\\":" ++ json(bookmarks)'
    ' ++ ",\\\"local_bookmarks\\\":" ++ json(local_bookmarks)'
    ' ++ ",\\\"tags\\\":" ++ json(tags)'
    ' ++ ",\\\"empty\\\":" ++ json(empty)'
    ' ++ ",\\\"conflict\\\":" ++ json(conflict)'
    ' ++ ",\\\"hidden\\\":" ++ json(hidden)'
    ")"
)

# Separator used between multiple log entries
SEPARATOR = "<<JJ_SEP>>"

# Template with separator for multi-change output
CHANGE_LIST_TEMPLATE = CHANGE_TEMPLATE + f' ++ "{SEPARATOR}"'


def parse_changes(output: str) -> list[Change]:
    """Parse multiple Change objects from jj log output."""
    output = output.strip()
    if not output:
        return []
    parts = output.split(SEPARATOR)
    changes: list[Change] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        data = json.loads(part)
        changes.append(Change.from_json(data))
    return changes


def parse_change(output: str) -> Change:
    """Parse a single Change object from jj output."""
    data = json.loads(output.strip())
    return Change.from_json(data)
