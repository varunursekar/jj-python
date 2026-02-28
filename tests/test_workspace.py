"""Tests for WorkspaceManager."""

import pytest

from .conftest import MockExecutor, make_repo


@pytest.fixture
def mx():
    return MockExecutor()


@pytest.fixture
def wm(mx):
    rp = make_repo(mx)
    return rp.workspace, mx


class TestWorkspaceAdd:
    @pytest.mark.asyncio
    async def test_add_basic(self, wm):
        mgr, mx = wm
        mx.queue(stdout="")
        await mgr.add("/tmp/new-ws")
        cmd = mx.calls[0]
        assert "workspace" in cmd
        assert "add" in cmd
        assert "/tmp/new-ws" in cmd

    @pytest.mark.asyncio
    async def test_add_with_name(self, wm):
        mgr, mx = wm
        mx.queue(stdout="")
        await mgr.add("/tmp/new-ws", name="my-ws")
        cmd = mx.calls[0]
        assert "--name" in cmd
        idx = cmd.index("--name")
        assert cmd[idx + 1] == "my-ws"


class TestWorkspaceForget:
    @pytest.mark.asyncio
    async def test_forget_single(self, wm):
        mgr, mx = wm
        mx.queue(stdout="")
        await mgr.forget("old-ws")
        cmd = mx.calls[0]
        assert "workspace" in cmd
        assert "forget" in cmd
        assert "old-ws" in cmd

    @pytest.mark.asyncio
    async def test_forget_multiple(self, wm):
        mgr, mx = wm
        mx.queue(stdout="")
        await mgr.forget("ws1", "ws2")
        cmd = mx.calls[0]
        assert "ws1" in cmd
        assert "ws2" in cmd


class TestWorkspaceList:
    @pytest.mark.asyncio
    async def test_list_parses_names(self, wm):
        mgr, mx = wm
        mx.queue(
            stdout="default: abc123 (no description)\nsecond: def456 (my workspace)\n"
        )
        result = await mgr.list()
        assert result == ["default", "second"]

    @pytest.mark.asyncio
    async def test_list_empty(self, wm):
        mgr, mx = wm
        mx.queue(stdout="")
        result = await mgr.list()
        assert result == []


class TestWorkspaceRoot:
    @pytest.mark.asyncio
    async def test_root_returns_stripped(self, wm):
        mgr, mx = wm
        mx.queue(stdout="/home/user/repo\n")
        result = await mgr.root()
        assert result == "/home/user/repo"


class TestWorkspaceUpdateStale:
    @pytest.mark.asyncio
    async def test_update_stale(self, wm):
        mgr, mx = wm
        mx.queue(stdout="")
        await mgr.update_stale()
        cmd = mx.calls[0]
        assert "workspace" in cmd
        assert "update-stale" in cmd
