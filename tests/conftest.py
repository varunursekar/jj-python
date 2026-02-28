"""Shared fixtures and helpers for jj tests."""

from __future__ import annotations

import json
import subprocess
from collections import deque
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from jj._executor import Executor


# ---------------------------------------------------------------------------
# MockExecutor
# ---------------------------------------------------------------------------


class MockExecutor:
    """Executor that records calls and returns queued results."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []
        self._responses: deque[subprocess.CompletedProcess[str]] = deque()

    def queue(
        self,
        stdout: str = "",
        stderr: str = "",
        returncode: int = 0,
    ) -> None:
        """Queue a CompletedProcess to be returned by the next execute() call."""
        self._responses.append(
            subprocess.CompletedProcess(
                args=[],
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
            )
        )

    async def execute(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        self.calls.append(cmd)
        if self._responses:
            resp = self._responses.popleft()
            # Fill in the actual args
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=resp.returncode,
                stdout=resp.stdout,
                stderr=resp.stderr,
            )
        # Default: success with empty output
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")


# ---------------------------------------------------------------------------
# Runner / Repo helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_executor() -> MockExecutor:
    return MockExecutor()


def make_runner(executor: MockExecutor, *, repo_path=None, jj_path="jj"):
    """Create a Runner with shutil.which patched so no real jj is needed."""
    from jj._runner import Runner

    with patch("jj._runner.shutil.which", return_value="/usr/bin/jj"):
        return Runner(jj_path=jj_path, repo_path=repo_path, executor=executor)


@pytest.fixture
def runner(mock_executor: MockExecutor):
    return make_runner(mock_executor)


def make_repo(executor: MockExecutor, *, path=None, jj_path="jj"):
    """Create a Repo backed by a MockExecutor."""
    from jj.repo import Repo

    with patch("jj._runner.shutil.which", return_value="/usr/bin/jj"):
        return Repo(path, jj_path=jj_path, executor=executor)


@pytest.fixture
def repo(mock_executor: MockExecutor):
    return make_repo(mock_executor)


# ---------------------------------------------------------------------------
# JSON fixture helpers
# ---------------------------------------------------------------------------

_TS = "2025-01-15T10:30:00+00:00"


def make_signature_json(
    name: str = "Test User",
    email: str = "test@example.com",
    timestamp: str = _TS,
) -> dict:
    return {"name": name, "email": email, "timestamp": timestamp}


def make_change_json(
    change_id: str = "abcdef12",
    commit_id: str = "deadbeef",
    parents: list[str] | None = None,
    description: str = "test change",
    author: dict | None = None,
    committer: dict | None = None,
    bookmarks: list | None = None,
    local_bookmarks: list | None = None,
    tags: list | None = None,
    empty: bool = False,
    conflict: bool = False,
    hidden: bool = False,
    *,
    wrap_base: bool = True,
) -> dict:
    """Build a Change JSON dict matching the template format."""
    inner = {
        "change_id": change_id,
        "commit_id": commit_id,
        "parents": parents or ["00000000"],
        "description": description,
        "author": author or make_signature_json(),
        "committer": committer or make_signature_json(),
    }
    if wrap_base:
        return {
            "base": inner,
            "bookmarks": bookmarks or [],
            "local_bookmarks": local_bookmarks or [],
            "tags": tags or [],
            "empty": empty,
            "conflict": conflict,
            "hidden": hidden,
        }
    # Flat format (no base wrapper)
    return {
        **inner,
        "bookmarks": bookmarks or [],
        "local_bookmarks": local_bookmarks or [],
        "tags": tags or [],
        "empty": empty,
        "conflict": conflict,
        "hidden": hidden,
    }


def change_stdout(change_json: dict) -> str:
    """Serialize a change dict to a JSON string (as jj would produce)."""
    return json.dumps(change_json)


def changes_stdout(*change_jsons: dict, separator: str = "<<JJ_SEP>>") -> str:
    """Serialize multiple change dicts with the separator."""
    return separator.join(json.dumps(c) for c in change_jsons) + separator
