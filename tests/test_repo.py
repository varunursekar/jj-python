"""Tests for Repo core methods — verifies args passed to executor and parsed returns."""

import pytest

from jj.repo import Status

from .conftest import (
    MockExecutor,
    change_stdout,
    changes_stdout,
    make_change_json,
    make_repo,
)


@pytest.fixture
def mx():
    return MockExecutor()


@pytest.fixture
def rp(mx):
    return make_repo(mx)


class TestLog:
    @pytest.mark.asyncio
    async def test_log_default_revset(self, mx, rp):
        c = make_change_json(change_id="log1")
        mx.queue(stdout=changes_stdout(c))
        await rp.log()
        cmd = mx.calls[0]
        assert "log" in cmd
        assert "-r" in cmd
        idx = cmd.index("-r")
        assert cmd[idx + 1] == "@"

    @pytest.mark.asyncio
    async def test_log_custom_revset(self, mx, rp):
        c = make_change_json(change_id="log2")
        mx.queue(stdout=changes_stdout(c))
        await rp.log(revset="main..@")
        cmd = mx.calls[0]
        idx = cmd.index("-r")
        assert cmd[idx + 1] == "main..@"

    @pytest.mark.asyncio
    async def test_log_with_limit(self, mx, rp):
        c = make_change_json()
        mx.queue(stdout=changes_stdout(c))
        await rp.log(limit=5)
        cmd = mx.calls[0]
        assert "-n" in cmd
        idx = cmd.index("-n")
        assert cmd[idx + 1] == "5"

    @pytest.mark.asyncio
    async def test_log_returns_changes(self, mx, rp):
        c1 = make_change_json(change_id="a")
        c2 = make_change_json(change_id="b")
        mx.queue(stdout=changes_stdout(c1, c2))
        result = await rp.log()
        assert len(result) == 2
        assert result[0].change_id == "a"
        assert result[1].change_id == "b"

    @pytest.mark.asyncio
    async def test_log_empty_returns_empty_list(self, mx, rp):
        mx.queue(stdout="")
        result = await rp.log()
        assert result == []


class TestShow:
    @pytest.mark.asyncio
    async def test_show_default_rev(self, mx, rp):
        c = make_change_json(change_id="show1")
        mx.queue(stdout=change_stdout(c))
        result = await rp.show()
        cmd = mx.calls[0]
        assert "-r" in cmd
        idx = cmd.index("-r")
        assert cmd[idx + 1] == "@"
        assert "-n" in cmd
        assert result.change_id == "show1"

    @pytest.mark.asyncio
    async def test_show_custom_rev(self, mx, rp):
        c = make_change_json(change_id="show2")
        mx.queue(stdout=change_stdout(c))
        await rp.show("abc")
        cmd = mx.calls[0]
        idx = cmd.index("-r")
        assert cmd[idx + 1] == "abc"


class TestDiff:
    @pytest.mark.asyncio
    async def test_diff_summary_default(self, mx, rp):
        mx.queue(stdout="M foo.py\nA bar.py\n")
        result = await rp.diff()
        cmd = mx.calls[0]
        assert "diff" in cmd
        assert "--summary" in cmd
        assert len(result.entries) == 2

    @pytest.mark.asyncio
    async def test_diff_with_revision(self, mx, rp):
        mx.queue(stdout="")
        await rp.diff(revision="abc")
        cmd = mx.calls[0]
        assert "-r" in cmd
        idx = cmd.index("-r")
        assert cmd[idx + 1] == "abc"

    @pytest.mark.asyncio
    async def test_diff_with_from_to(self, mx, rp):
        mx.queue(stdout="")
        await rp.diff(from_rev="a", to_rev="b")
        cmd = mx.calls[0]
        assert "--from" in cmd
        assert "--to" in cmd

    @pytest.mark.asyncio
    async def test_diff_git_flag(self, mx, rp):
        mx.queue(stdout="diff --git a/x b/x\n")
        result = await rp.diff_git()
        cmd = mx.calls[0]
        assert "diff" in cmd
        assert "--git" in cmd
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_diff_git_with_revision(self, mx, rp):
        mx.queue(stdout="")
        await rp.diff_git(revision="abc")
        cmd = mx.calls[0]
        assert "-r" in cmd
        assert "--git" in cmd


class TestStatus:
    @pytest.mark.asyncio
    async def test_status_composes_show_and_diff(self, mx, rp):
        c = make_change_json(change_id="wc")
        mx.queue(stdout=change_stdout(c))  # show("@")
        mx.queue(stdout="M readme.md\n")  # diff()
        result = await rp.status()
        assert isinstance(result, Status)
        assert result.working_copy.change_id == "wc"
        assert len(result.diff.entries) == 1
        # Two calls: show + diff
        assert len(mx.calls) == 2


class TestFileList:
    @pytest.mark.asyncio
    async def test_file_list_parses_output(self, mx, rp):
        mx.queue(stdout="src/main.py\nsrc/lib.py\nREADME.md\n")
        result = await rp.file_list()
        assert result == ["src/main.py", "src/lib.py", "README.md"]
        cmd = mx.calls[0]
        assert "file" in cmd
        assert "list" in cmd

    @pytest.mark.asyncio
    async def test_file_list_with_revision(self, mx, rp):
        mx.queue(stdout="a.py\n")
        await rp.file_list(revision="main")
        cmd = mx.calls[0]
        assert "-r" in cmd
        idx = cmd.index("-r")
        assert cmd[idx + 1] == "main"

    @pytest.mark.asyncio
    async def test_file_list_empty(self, mx, rp):
        mx.queue(stdout="")
        result = await rp.file_list()
        assert result == []


class TestNew:
    @pytest.mark.asyncio
    async def test_new_basic(self, mx, rp):
        c = make_change_json(change_id="new1")
        mx.queue(stdout="")  # new
        mx.queue(stdout=change_stdout(c))  # show("@")
        result = await rp.new()
        assert "new" in mx.calls[0]
        assert result.change_id == "new1"

    @pytest.mark.asyncio
    async def test_new_with_revisions(self, mx, rp):
        c = make_change_json()
        mx.queue(stdout="")
        mx.queue(stdout=change_stdout(c))
        await rp.new("abc", "def")
        cmd = mx.calls[0]
        assert "abc" in cmd
        assert "def" in cmd

    @pytest.mark.asyncio
    async def test_new_with_message(self, mx, rp):
        c = make_change_json()
        mx.queue(stdout="")
        mx.queue(stdout=change_stdout(c))
        await rp.new(message="hello")
        cmd = mx.calls[0]
        assert "-m" in cmd
        idx = cmd.index("-m")
        assert cmd[idx + 1] == "hello"

    @pytest.mark.asyncio
    async def test_new_insert_before(self, mx, rp):
        c = make_change_json()
        mx.queue(stdout="")
        mx.queue(stdout=change_stdout(c))
        await rp.new("x", insert_before=True)
        assert "--insert-before" in mx.calls[0]

    @pytest.mark.asyncio
    async def test_new_insert_after(self, mx, rp):
        c = make_change_json()
        mx.queue(stdout="")
        mx.queue(stdout=change_stdout(c))
        await rp.new("x", insert_after=True)
        assert "--insert-after" in mx.calls[0]


class TestDescribe:
    @pytest.mark.asyncio
    async def test_describe_default_rev(self, mx, rp):
        c = make_change_json()
        mx.queue(stdout="")  # describe
        mx.queue(stdout=change_stdout(c))  # show
        await rp.describe(message="new desc")
        cmd = mx.calls[0]
        assert "describe" in cmd
        assert "@" in cmd
        assert "-m" in cmd
        idx = cmd.index("-m")
        assert cmd[idx + 1] == "new desc"

    @pytest.mark.asyncio
    async def test_describe_custom_rev(self, mx, rp):
        c = make_change_json()
        mx.queue(stdout="")
        mx.queue(stdout=change_stdout(c))
        await rp.describe("abc", message="x")
        cmd = mx.calls[0]
        assert "abc" in cmd

    @pytest.mark.asyncio
    async def test_describe_reset_author(self, mx, rp):
        c = make_change_json()
        mx.queue(stdout="")
        mx.queue(stdout=change_stdout(c))
        await rp.describe(message="x", reset_author=True)
        assert "--reset-author" in mx.calls[0]


class TestCommit:
    @pytest.mark.asyncio
    async def test_commit_args_and_returns_parent(self, mx, rp):
        c = make_change_json(change_id="committed")
        mx.queue(stdout="")  # commit
        mx.queue(stdout=change_stdout(c))  # show("@-")
        result = await rp.commit(message="done")
        cmd = mx.calls[0]
        assert "commit" in cmd
        assert "-m" in cmd
        idx = cmd.index("-m")
        assert cmd[idx + 1] == "done"
        # Second call should show @-
        show_cmd = mx.calls[1]
        assert "@-" in show_cmd
        assert result.change_id == "committed"


class TestEdit:
    @pytest.mark.asyncio
    async def test_edit_args(self, mx, rp):
        mx.queue(stdout="")
        await rp.edit("abc123")
        cmd = mx.calls[0]
        assert "edit" in cmd
        assert "abc123" in cmd


class TestSquash:
    @pytest.mark.asyncio
    async def test_squash_basic(self, mx, rp):
        mx.queue(stdout="")
        await rp.squash()
        assert "squash" in mx.calls[0]

    @pytest.mark.asyncio
    async def test_squash_with_options(self, mx, rp):
        mx.queue(stdout="")
        await rp.squash(revision="abc", into="def", message="squashed")
        cmd = mx.calls[0]
        assert "-r" in cmd
        assert "--into" in cmd
        assert "-m" in cmd


class TestSplit:
    @pytest.mark.asyncio
    async def test_split_with_files(self, mx, rp):
        mx.queue(stdout="")
        await rp.split(files=["a.py", "b.py"])
        cmd = mx.calls[0]
        assert "split" in cmd
        assert "--" in cmd
        assert "a.py" in cmd
        assert "b.py" in cmd

    @pytest.mark.asyncio
    async def test_split_with_revision(self, mx, rp):
        mx.queue(stdout="")
        await rp.split(revision="abc", files=["x.py"])
        cmd = mx.calls[0]
        assert "-r" in cmd
        idx = cmd.index("-r")
        assert cmd[idx + 1] == "abc"


class TestRebase:
    @pytest.mark.asyncio
    async def test_rebase_basic(self, mx, rp):
        mx.queue(stdout="")
        await rp.rebase(destination="main")
        cmd = mx.calls[0]
        assert "rebase" in cmd
        assert "-d" in cmd
        idx = cmd.index("-d")
        assert cmd[idx + 1] == "main"

    @pytest.mark.asyncio
    async def test_rebase_with_revision(self, mx, rp):
        mx.queue(stdout="")
        await rp.rebase(revision="abc", destination="main")
        assert "-r" in mx.calls[0]

    @pytest.mark.asyncio
    async def test_rebase_with_source(self, mx, rp):
        mx.queue(stdout="")
        await rp.rebase(source="abc", destination="main")
        assert "-s" in mx.calls[0]

    @pytest.mark.asyncio
    async def test_rebase_with_branch(self, mx, rp):
        mx.queue(stdout="")
        await rp.rebase(branch="feature", destination="main")
        assert "-b" in mx.calls[0]


class TestAbandon:
    @pytest.mark.asyncio
    async def test_abandon_default(self, mx, rp):
        mx.queue(stdout="")
        await rp.abandon()
        cmd = mx.calls[0]
        assert "abandon" in cmd
        assert "@" in cmd

    @pytest.mark.asyncio
    async def test_abandon_specific(self, mx, rp):
        mx.queue(stdout="")
        await rp.abandon("abc", "def")
        cmd = mx.calls[0]
        assert "abc" in cmd
        assert "def" in cmd


class TestRestore:
    @pytest.mark.asyncio
    async def test_restore_basic(self, mx, rp):
        mx.queue(stdout="")
        await rp.restore()
        assert "restore" in mx.calls[0]

    @pytest.mark.asyncio
    async def test_restore_with_options(self, mx, rp):
        mx.queue(stdout="")
        await rp.restore(revision="abc", from_rev="x", to_rev="y")
        cmd = mx.calls[0]
        assert "-r" in cmd
        assert "--from" in cmd
        assert "--to" in cmd


class TestDuplicate:
    @pytest.mark.asyncio
    async def test_duplicate_default(self, mx, rp):
        c = make_change_json(change_id="dup1")
        mx.queue(stdout="")  # duplicate
        mx.queue(stdout=changes_stdout(c))  # log
        result = await rp.duplicate()
        assert "duplicate" in mx.calls[0]
        assert "@" in mx.calls[0]
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_duplicate_specific(self, mx, rp):
        c1 = make_change_json(change_id="d1")
        c2 = make_change_json(change_id="d2")
        mx.queue(stdout="")
        mx.queue(stdout=changes_stdout(c1, c2))
        await rp.duplicate("abc", "def")
        cmd = mx.calls[0]
        assert "abc" in cmd
        assert "def" in cmd


class TestUndo:
    @pytest.mark.asyncio
    async def test_undo(self, mx, rp):
        mx.queue(stdout="")
        await rp.undo()
        assert mx.calls[0][-1] == "undo"


class TestRun:
    @pytest.mark.asyncio
    async def test_run_escape_hatch(self, mx, rp):
        mx.queue(stdout="custom output", returncode=0)
        result = await rp.run(["custom", "cmd"])
        cmd = mx.calls[0]
        assert "custom" in cmd
        assert "cmd" in cmd
        assert result.stdout == "custom output"

    @pytest.mark.asyncio
    async def test_run_check_false_by_default(self, mx, rp):
        mx.queue(returncode=1, stderr="err")
        result = await rp.run(["failing"])
        # Should not raise
        assert result.returncode == 1
