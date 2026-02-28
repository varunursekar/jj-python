"""Tests for model classes — pure data parsing, no async."""

from datetime import datetime, timezone

from jj.models import Bookmark, Change, DiffEntry, DiffSummary, Operation, Signature, _extract_names

from .conftest import make_change_json, make_signature_json


class TestSignature:
    def test_from_json(self):
        data = make_signature_json(
            name="Alice",
            email="alice@example.com",
            timestamp="2025-01-15T10:30:00+00:00",
        )
        sig = Signature.from_json(data)
        assert sig.name == "Alice"
        assert sig.email == "alice@example.com"
        assert sig.timestamp == datetime(2025, 1, 15, 10, 30, tzinfo=timezone.utc)

    def test_from_json_naive_timestamp(self):
        data = make_signature_json(timestamp="2025-06-01T12:00:00")
        sig = Signature.from_json(data)
        assert sig.timestamp.year == 2025
        assert sig.timestamp.month == 6


class TestExtractNames:
    def test_object_format(self):
        items = [{"name": "main", "target": ["abc"]}, {"name": "dev", "target": ["def"]}]
        assert _extract_names(items) == ["main", "dev"]

    def test_string_format(self):
        items = ["main", "dev"]
        assert _extract_names(items) == ["main", "dev"]

    def test_mixed(self):
        items = [{"name": "main", "target": []}, "dev"]
        assert _extract_names(items) == ["main", "dev"]

    def test_empty(self):
        assert _extract_names([]) == []


class TestChange:
    def test_from_json_with_base_wrapper(self):
        data = make_change_json(
            change_id="abc123",
            commit_id="def456",
            description="hello world",
            bookmarks=[{"name": "main", "target": ["x"]}],
            empty=True,
        )
        c = Change.from_json(data)
        assert c.change_id == "abc123"
        assert c.commit_id == "def456"
        assert c.description == "hello world"
        assert c.bookmarks == ["main"]
        assert c.empty is True
        assert c.conflict is False
        assert c.hidden is False

    def test_from_json_without_base_wrapper(self):
        data = make_change_json(wrap_base=False, change_id="flat1")
        c = Change.from_json(data)
        assert c.change_id == "flat1"

    def test_from_json_conflict_and_hidden(self):
        data = make_change_json(conflict=True, hidden=True)
        c = Change.from_json(data)
        assert c.conflict is True
        assert c.hidden is True

    def test_from_json_local_bookmarks_and_tags(self):
        data = make_change_json(
            local_bookmarks=[{"name": "feature", "target": []}],
            tags=[{"name": "v1.0", "target": []}],
        )
        c = Change.from_json(data)
        assert c.local_bookmarks == ["feature"]
        assert c.tags == ["v1.0"]

    def test_parents(self):
        data = make_change_json(parents=["parent1", "parent2"])
        c = Change.from_json(data)
        assert c.parents == ["parent1", "parent2"]


class TestDiffSummary:
    def test_modified_added_deleted(self):
        text = "M src/main.py\nA src/new.py\nD src/old.py\n"
        ds = DiffSummary.parse(text)
        assert len(ds.entries) == 3
        assert ds.entries[0] == DiffEntry(status="M", path="src/main.py")
        assert ds.entries[1] == DiffEntry(status="A", path="src/new.py")
        assert ds.entries[2] == DiffEntry(status="D", path="src/old.py")

    def test_rename(self):
        text = "R {old.py => new.py}\n"
        ds = DiffSummary.parse(text)
        assert len(ds.entries) == 1
        entry = ds.entries[0]
        assert entry.status == "R"
        assert entry.path == "new.py"
        assert entry.from_path == "old.py"

    def test_empty_input(self):
        assert DiffSummary.parse("").entries == []
        assert DiffSummary.parse("   \n\n  ").entries == []

    def test_whitespace_handling(self):
        text = "  M  foo.py  \n  A  bar.py  \n"
        ds = DiffSummary.parse(text)
        assert len(ds.entries) == 2
        assert ds.entries[0].status == "M"
        assert ds.entries[1].status == "A"


class TestBookmark:
    def test_construction(self):
        b = Bookmark(name="main", present=True, tracking="origin")
        assert b.name == "main"
        assert b.present is True
        assert b.tracking == "origin"

    def test_defaults(self):
        b = Bookmark(name="dev")
        assert b.present is True
        assert b.tracking is None


class TestOperation:
    def test_construction(self):
        op = Operation(
            id="abc123",
            description="create change",
            time="2025-01-15 10:30",
            user="test@host",
            tags="",
        )
        assert op.id == "abc123"
        assert op.description == "create change"
