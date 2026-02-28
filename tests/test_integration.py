"""Integration tests that run real jj commands against temp repos.

These tests require jj to be installed. They are automatically skipped
if jj is not found on PATH.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from jj._executor import LocalExecutor
from jj.errors import JJCommandError, JJRepoNotFoundError
from jj.models import Bookmark, Change, DiffSummary
from jj.repo import Repo, Status

pytestmark = pytest.mark.skipif(
    shutil.which("jj") is None,
    reason="jj binary not found on PATH",
)


@pytest.fixture
async def tmp_repo(tmp_path: Path) -> Repo:
    """Create a real jj repo in a temp directory and return a Repo."""
    # Init without --repository since the repo doesn't exist yet
    executor = LocalExecutor()
    await executor.execute(["jj", "git", "init", str(tmp_path)])
    return Repo(tmp_path)


class TestIntegrationLog:
    @pytest.mark.asyncio
    async def test_log_returns_changes(self, tmp_repo: Repo):
        changes = await tmp_repo.log()
        assert isinstance(changes, list)
        # A fresh repo has at least the root change
        assert len(changes) >= 1
        assert isinstance(changes[0], Change)

    @pytest.mark.asyncio
    async def test_log_with_limit(self, tmp_repo: Repo):
        changes = await tmp_repo.log(limit=1)
        assert len(changes) == 1

    @pytest.mark.asyncio
    async def test_log_with_revset(self, tmp_repo: Repo):
        changes = await tmp_repo.log(revset="@")
        assert len(changes) == 1


class TestIntegrationShow:
    @pytest.mark.asyncio
    async def test_show_working_copy(self, tmp_repo: Repo):
        change = await tmp_repo.show()
        assert isinstance(change, Change)
        assert change.change_id
        assert change.commit_id

    @pytest.mark.asyncio
    async def test_show_fields(self, tmp_repo: Repo):
        change = await tmp_repo.show()
        # author.name may be empty if jj user not configured
        assert isinstance(change.author.name, str)
        assert isinstance(change.parents, list)


class TestIntegrationDescribe:
    @pytest.mark.asyncio
    async def test_describe_and_read_back(self, tmp_repo: Repo):
        await tmp_repo.describe(message="integration test msg")
        change = await tmp_repo.show()
        # jj descriptions include a trailing newline
        assert change.description.strip() == "integration test msg"

    @pytest.mark.asyncio
    async def test_describe_reset_author(self, tmp_repo: Repo):
        result = await tmp_repo.describe(message="with reset", reset_author=True)
        assert isinstance(result, Change)


class TestIntegrationDiff:
    @pytest.mark.asyncio
    async def test_diff_empty_repo(self, tmp_repo: Repo):
        ds = await tmp_repo.diff()
        assert isinstance(ds, DiffSummary)

    @pytest.mark.asyncio
    async def test_diff_after_file_change(self, tmp_repo: Repo):
        repo_path = Path(str(tmp_repo._runner.repo_path))
        (repo_path / "hello.txt").write_text("hello world\n")
        ds = await tmp_repo.diff()
        # Paths may be relative to CWD when using --repository
        assert any(e.path.endswith("hello.txt") for e in ds.entries)

    @pytest.mark.asyncio
    async def test_diff_git(self, tmp_repo: Repo):
        repo_path = Path(str(tmp_repo._runner.repo_path))
        (repo_path / "test.txt").write_text("data\n")
        result = await tmp_repo.diff_git()
        assert isinstance(result, str)


class TestIntegrationStatus:
    @pytest.mark.asyncio
    async def test_status(self, tmp_repo: Repo):
        status = await tmp_repo.status()
        assert isinstance(status, Status)
        assert isinstance(status.working_copy, Change)
        assert isinstance(status.diff, DiffSummary)


class TestIntegrationFileList:
    @pytest.mark.asyncio
    async def test_file_list_empty_repo(self, tmp_repo: Repo):
        files = await tmp_repo.file_list()
        assert isinstance(files, list)

    @pytest.mark.asyncio
    async def test_file_list_after_adding_file(self, tmp_repo: Repo):
        repo_path = Path(str(tmp_repo._runner.repo_path))
        (repo_path / "tracked.txt").write_text("tracked\n")
        files = await tmp_repo.file_list()
        # Paths may be relative to CWD when using --repository
        assert any(f.endswith("tracked.txt") for f in files)


class TestIntegrationNew:
    @pytest.mark.asyncio
    async def test_new_creates_change(self, tmp_repo: Repo):
        old = await tmp_repo.show()
        new = await tmp_repo.new()
        assert isinstance(new, Change)
        assert new.change_id != old.change_id

    @pytest.mark.asyncio
    async def test_new_with_message(self, tmp_repo: Repo):
        new = await tmp_repo.new(message="from new")
        assert new.description.strip() == "from new"


class TestIntegrationCommit:
    @pytest.mark.asyncio
    async def test_commit(self, tmp_repo: Repo):
        await tmp_repo.describe(message="about to commit")
        result = await tmp_repo.commit(message="committed")
        assert isinstance(result, Change)
        assert result.description.strip() == "committed"


class TestIntegrationEdit:
    @pytest.mark.asyncio
    async def test_edit_switches_working_copy(self, tmp_repo: Repo):
        original = await tmp_repo.show()
        await tmp_repo.new()
        await tmp_repo.edit(original.change_id)
        current = await tmp_repo.show()
        assert current.change_id == original.change_id


class TestIntegrationAbandon:
    @pytest.mark.asyncio
    async def test_abandon_current(self, tmp_repo: Repo):
        old = await tmp_repo.show()
        await tmp_repo.abandon()
        new = await tmp_repo.show()
        assert new.change_id != old.change_id


class TestIntegrationDuplicate:
    @pytest.mark.asyncio
    async def test_duplicate(self, tmp_repo: Repo):
        await tmp_repo.describe(message="to duplicate")
        result = await tmp_repo.duplicate("@")
        assert isinstance(result, list)
        assert len(result) >= 1


class TestIntegrationUndo:
    @pytest.mark.asyncio
    async def test_undo(self, tmp_repo: Repo):
        await tmp_repo.describe(message="before undo")
        await tmp_repo.describe(message="will undo this")
        await tmp_repo.undo()
        change = await tmp_repo.show()
        assert change.description.strip() == "before undo"


class TestIntegrationBookmarks:
    @pytest.mark.asyncio
    async def test_create_and_list(self, tmp_repo: Repo):
        await tmp_repo.bookmark.create("test-bm")
        bookmarks = await tmp_repo.bookmark.list()
        names = [b.name for b in bookmarks]
        assert "test-bm" in names

    @pytest.mark.asyncio
    async def test_delete(self, tmp_repo: Repo):
        await tmp_repo.bookmark.create("to-delete")
        await tmp_repo.bookmark.delete("to-delete")
        bookmarks = await tmp_repo.bookmark.list()
        names = [b.name for b in bookmarks]
        assert "to-delete" not in names

    @pytest.mark.asyncio
    async def test_rename(self, tmp_repo: Repo):
        await tmp_repo.bookmark.create("old-name")
        await tmp_repo.bookmark.rename("old-name", "new-name")
        bookmarks = await tmp_repo.bookmark.list()
        names = [b.name for b in bookmarks]
        assert "new-name" in names
        assert "old-name" not in names


class TestIntegrationWorkspace:
    @pytest.mark.asyncio
    async def test_list(self, tmp_repo: Repo):
        names = await tmp_repo.workspace.list()
        assert "default" in names

    @pytest.mark.asyncio
    async def test_root(self, tmp_repo: Repo):
        root = await tmp_repo.workspace.root()
        assert root  # non-empty


class TestIntegrationOperations:
    @pytest.mark.asyncio
    async def test_op_log(self, tmp_repo: Repo):
        ops = await tmp_repo.op.log()
        assert len(ops) >= 1
        assert ops[0].id  # has an id

    @pytest.mark.asyncio
    async def test_op_log_with_limit(self, tmp_repo: Repo):
        ops = await tmp_repo.op.log(limit=1)
        assert len(ops) == 1

    @pytest.mark.asyncio
    async def test_op_log_contains_init(self, tmp_repo: Repo):
        ops = await tmp_repo.op.log()
        descriptions = [op.description.lower() for op in ops]
        assert any("add workspace" in d or "init" in d for d in descriptions)


class TestIntegrationRun:
    @pytest.mark.asyncio
    async def test_run_arbitrary_command(self, tmp_repo: Repo):
        result = await tmp_repo.run(["version"])
        assert "jj" in result.stdout.lower()


class TestIntegrationRepoNotFound:
    @pytest.mark.asyncio
    async def test_repo_not_found(self, tmp_path: Path):
        non_repo = tmp_path / "not-a-repo"
        non_repo.mkdir()
        repo = Repo(non_repo)
        with pytest.raises((JJRepoNotFoundError, JJCommandError)):
            await repo.log()
