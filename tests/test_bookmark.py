"""Tests for BookmarkManager."""

import pytest

from .conftest import MockExecutor, make_repo


@pytest.fixture
def mx():
    return MockExecutor()


@pytest.fixture
def bm(mx):
    rp = make_repo(mx)
    return rp.bookmark, mx


class TestBookmarkList:
    @pytest.mark.asyncio
    async def test_list_parses_names(self, bm):
        mgr, mx = bm
        mx.queue(stdout="main: abc123 def456\ndev: 111222 333444\n")
        result = await mgr.list()
        assert len(result) == 2
        assert result[0].name == "main"
        assert result[1].name == "dev"

    @pytest.mark.asyncio
    async def test_list_detects_deleted(self, bm):
        mgr, mx = bm
        mx.queue(stdout="old-branch: abc123 (deleted)\n")
        result = await mgr.list()
        assert len(result) == 1
        assert result[0].name == "old-branch"
        assert result[0].present is False

    @pytest.mark.asyncio
    async def test_list_detects_remote_tracking(self, bm):
        mgr, mx = bm
        mx.queue(stdout="main@origin: abc123 def456\n")
        result = await mgr.list()
        assert len(result) == 1
        assert result[0].name == "main"
        assert result[0].tracking == "origin"

    @pytest.mark.asyncio
    async def test_list_all_remotes_flag(self, bm):
        mgr, mx = bm
        mx.queue(stdout="")
        await mgr.list(all_remotes=True)
        assert "--all-remotes" in mx.calls[0]

    @pytest.mark.asyncio
    async def test_list_no_all_remotes_by_default(self, bm):
        mgr, mx = bm
        mx.queue(stdout="")
        await mgr.list()
        assert "--all-remotes" not in mx.calls[0]


class TestBookmarkCreate:
    @pytest.mark.asyncio
    async def test_create_basic(self, bm):
        mgr, mx = bm
        mx.queue(stdout="")
        await mgr.create("feature")
        cmd = mx.calls[0]
        assert "bookmark" in cmd
        assert "create" in cmd
        assert "feature" in cmd

    @pytest.mark.asyncio
    async def test_create_with_revision(self, bm):
        mgr, mx = bm
        mx.queue(stdout="")
        await mgr.create("feature", revision="abc")
        cmd = mx.calls[0]
        assert "-r" in cmd
        idx = cmd.index("-r")
        assert cmd[idx + 1] == "abc"


class TestBookmarkDelete:
    @pytest.mark.asyncio
    async def test_delete(self, bm):
        mgr, mx = bm
        mx.queue(stdout="")
        await mgr.delete("main", "dev")
        cmd = mx.calls[0]
        assert "bookmark" in cmd
        assert "delete" in cmd
        assert "main" in cmd
        assert "dev" in cmd


class TestBookmarkForget:
    @pytest.mark.asyncio
    async def test_forget(self, bm):
        mgr, mx = bm
        mx.queue(stdout="")
        await mgr.forget("old")
        cmd = mx.calls[0]
        assert "bookmark" in cmd
        assert "forget" in cmd
        assert "old" in cmd


class TestBookmarkMove:
    @pytest.mark.asyncio
    async def test_move_basic(self, bm):
        mgr, mx = bm
        mx.queue(stdout="")
        await mgr.move("main")
        cmd = mx.calls[0]
        assert "bookmark" in cmd
        assert "move" in cmd
        assert "main" in cmd

    @pytest.mark.asyncio
    async def test_move_with_to(self, bm):
        mgr, mx = bm
        mx.queue(stdout="")
        await mgr.move("main", to="abc")
        cmd = mx.calls[0]
        assert "--to" in cmd
        idx = cmd.index("--to")
        assert cmd[idx + 1] == "abc"


class TestBookmarkSet:
    @pytest.mark.asyncio
    async def test_set_basic(self, bm):
        mgr, mx = bm
        mx.queue(stdout="")
        await mgr.set("feature")
        cmd = mx.calls[0]
        assert "bookmark" in cmd
        assert "set" in cmd
        assert "feature" in cmd

    @pytest.mark.asyncio
    async def test_set_with_revision(self, bm):
        mgr, mx = bm
        mx.queue(stdout="")
        await mgr.set("feature", revision="abc")
        assert "-r" in mx.calls[0]


class TestBookmarkRename:
    @pytest.mark.asyncio
    async def test_rename(self, bm):
        mgr, mx = bm
        mx.queue(stdout="")
        await mgr.rename("old-name", "new-name")
        cmd = mx.calls[0]
        assert "bookmark" in cmd
        assert "rename" in cmd
        assert "old-name" in cmd
        assert "new-name" in cmd


class TestBookmarkTrack:
    @pytest.mark.asyncio
    async def test_track_default_remote(self, bm):
        mgr, mx = bm
        mx.queue(stdout="")
        await mgr.track("main")
        cmd = mx.calls[0]
        assert "bookmark" in cmd
        assert "track" in cmd
        assert "main@origin" in cmd

    @pytest.mark.asyncio
    async def test_track_custom_remote(self, bm):
        mgr, mx = bm
        mx.queue(stdout="")
        await mgr.track("main", remote="upstream")
        assert "main@upstream" in mx.calls[0]


class TestBookmarkUntrack:
    @pytest.mark.asyncio
    async def test_untrack_default_remote(self, bm):
        mgr, mx = bm
        mx.queue(stdout="")
        await mgr.untrack("main")
        cmd = mx.calls[0]
        assert "bookmark" in cmd
        assert "untrack" in cmd
        assert "main@origin" in cmd

    @pytest.mark.asyncio
    async def test_untrack_custom_remote(self, bm):
        mgr, mx = bm
        mx.queue(stdout="")
        await mgr.untrack("main", remote="upstream")
        assert "main@upstream" in mx.calls[0]
