from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Signature:
    """Author or committer identity."""

    name: str
    email: str
    timestamp: datetime

    @classmethod
    def from_json(cls, data: dict) -> Signature:
        return cls(
            name=data["name"],
            email=data["email"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )


def _extract_names(items: list) -> list[str]:
    """Extract name strings from json(bookmarks)/json(tags) output.

    These are lists of ``{"name": "...", "target": [...]}`` objects.
    """
    return [item["name"] if isinstance(item, dict) else item for item in items]


@dataclass(frozen=True)
class Change:
    """A jj change (commit) with its metadata."""

    change_id: str
    commit_id: str
    parents: list[str]
    description: str
    author: Signature
    committer: Signature
    bookmarks: list[str] = field(default_factory=list)
    local_bookmarks: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    empty: bool = False
    conflict: bool = False
    hidden: bool = False

    @classmethod
    def from_json(cls, data: dict) -> Change:
        base = data.get("base", data)
        return cls(
            change_id=base["change_id"],
            commit_id=base["commit_id"],
            parents=base["parents"],
            description=base["description"],
            author=Signature.from_json(base["author"]),
            committer=Signature.from_json(base["committer"]),
            bookmarks=_extract_names(data.get("bookmarks", [])),
            local_bookmarks=_extract_names(data.get("local_bookmarks", [])),
            tags=_extract_names(data.get("tags", [])),
            empty=data.get("empty", False),
            conflict=data.get("conflict", False),
            hidden=data.get("hidden", False),
        )


@dataclass(frozen=True)
class DiffEntry:
    """A single file entry in a diff summary."""

    status: str  # "M", "A", "D", "R"
    path: str
    from_path: str | None = None  # set for renames


@dataclass(frozen=True)
class DiffSummary:
    """Parsed output of jj diff --summary."""

    entries: list[DiffEntry]

    @classmethod
    def parse(cls, text: str) -> DiffSummary:
        entries: list[DiffEntry] = []
        for line in text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # Format: "M path" or "R {from => to}"
            status = line[0]
            rest = line[1:].strip()
            if status == "R" and " => " in rest:
                rest = rest.strip("{}")
                from_path, _, to_path = rest.partition(" => ")
                entries.append(
                    DiffEntry(status=status, path=to_path.strip(), from_path=from_path.strip())
                )
            else:
                entries.append(DiffEntry(status=status, path=rest))
        return cls(entries=entries)


@dataclass(frozen=True)
class Bookmark:
    """A jj bookmark."""

    name: str
    present: bool = True
    tracking: str | None = None  # e.g. "origin" if tracking a remote


@dataclass(frozen=True)
class Operation:
    """A jj operation log entry."""

    id: str
    description: str
    time: str
    user: str
    tags: str
