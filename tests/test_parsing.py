"""Tests for template output parsing."""

import json

from jj._parsing import (
    CHANGE_LIST_TEMPLATE,
    CHANGE_TEMPLATE,
    SEPARATOR,
    parse_change,
    parse_changes,
)

from .conftest import change_stdout, changes_stdout, make_change_json


class TestTemplateConstants:
    def test_change_template_is_nonempty(self):
        assert isinstance(CHANGE_TEMPLATE, str)
        assert len(CHANGE_TEMPLATE) > 0

    def test_change_list_template_is_nonempty(self):
        assert isinstance(CHANGE_LIST_TEMPLATE, str)
        assert len(CHANGE_LIST_TEMPLATE) > 0

    def test_separator_is_nonempty(self):
        assert isinstance(SEPARATOR, str)
        assert len(SEPARATOR) > 0

    def test_list_template_contains_separator(self):
        assert SEPARATOR in CHANGE_LIST_TEMPLATE


class TestParseChange:
    def test_single_change(self):
        data = make_change_json(change_id="single1", description="hello")
        c = parse_change(change_stdout(data))
        assert c.change_id == "single1"
        assert c.description == "hello"

    def test_with_whitespace(self):
        data = make_change_json(change_id="ws1")
        text = "  \n" + change_stdout(data) + "\n  "
        c = parse_change(text)
        assert c.change_id == "ws1"


class TestParseChanges:
    def test_empty_output(self):
        assert parse_changes("") == []
        assert parse_changes("   \n  ") == []

    def test_single_change(self):
        data = make_change_json(change_id="one")
        result = parse_changes(changes_stdout(data))
        assert len(result) == 1
        assert result[0].change_id == "one"

    def test_multiple_changes(self):
        c1 = make_change_json(change_id="first")
        c2 = make_change_json(change_id="second")
        c3 = make_change_json(change_id="third")
        result = parse_changes(changes_stdout(c1, c2, c3))
        assert [c.change_id for c in result] == ["first", "second", "third"]

    def test_trailing_separator_ignored(self):
        data = make_change_json(change_id="trail")
        text = json.dumps(data) + "<<JJ_SEP>>"
        result = parse_changes(text)
        assert len(result) == 1
