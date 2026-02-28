"""Tests for OperationManager."""

import pytest

from jj._operation import OperationManager

from .conftest import MockExecutor, make_repo


@pytest.fixture
def mx():
    return MockExecutor()


@pytest.fixture
def om(mx):
    rp = make_repo(mx)
    return rp.op, mx


class TestOperationLog:
    @pytest.mark.asyncio
    async def test_log_basic(self, om):
        mgr, mx = om
        mx.queue(stdout="")
        await mgr.log()
        cmd = mx.calls[0]
        assert "operation" in cmd
        assert "log" in cmd
        assert "--no-graph" in cmd

    @pytest.mark.asyncio
    async def test_log_with_limit(self, om):
        mgr, mx = om
        mx.queue(stdout="")
        await mgr.log(limit=10)
        cmd = mx.calls[0]
        assert "-n" in cmd
        idx = cmd.index("-n")
        assert cmd[idx + 1] == "10"

    @pytest.mark.asyncio
    async def test_log_parses_output(self, om):
        mgr, mx = om
        output = (
            "abc123 user@host 5 seconds ago, lasted 10ms\n"
            "new empty commit\n"
            "args: jj new -m hello\n"
            "\n"
            "def456 user@host 10 seconds ago, lasted 12ms\n"
            "describe commit deadbeef\n"
            "args: jj describe -m world\n"
        )
        mx.queue(stdout=output)
        result = await mgr.log()
        assert len(result) == 2
        assert result[0].id == "abc123"
        assert result[0].description == "new empty commit"
        assert result[0].user == "user@host"
        assert result[1].id == "def456"
        assert result[1].description == "describe commit deadbeef"


class TestParseOpLog:
    def test_parse_single_op(self):
        text = (
            "abc123 admin@host now, lasted 5ms\n"
            "init repo\n"
            "args: jj git init\n"
        )
        ops = OperationManager._parse_op_log(text)
        assert len(ops) == 1
        assert ops[0].id == "abc123"
        assert ops[0].description == "init repo"
        assert ops[0].user == "admin@host"
        assert ops[0].tags == "jj git init"

    def test_parse_multiple_ops_separated_by_blank_lines(self):
        text = (
            "op1 u1@host 1 second ago, lasted 10ms\n"
            "first operation\n"
            "args: jj new\n"
            "\n"
            "op2 u2@host 2 seconds ago, lasted 12ms\n"
            "second operation\n"
            "args: jj describe\n"
        )
        ops = OperationManager._parse_op_log(text)
        assert len(ops) == 2
        assert ops[0].id == "op1"
        assert ops[0].description == "first operation"
        assert ops[1].id == "op2"
        assert ops[1].description == "second operation"

    def test_parse_root_operation(self):
        text = "000000000000 root()\n"
        ops = OperationManager._parse_op_log(text)
        assert len(ops) == 1
        assert ops[0].id == "000000000000"
        assert ops[0].user == "root()"

    def test_parse_entry_without_args_line(self):
        text = (
            "abc123 user@host now, lasted 5ms\n"
            "add workspace 'default'\n"
        )
        ops = OperationManager._parse_op_log(text)
        assert len(ops) == 1
        assert ops[0].id == "abc123"
        assert ops[0].description == "add workspace 'default'"
        assert ops[0].tags == ""

    def test_parse_empty(self):
        assert OperationManager._parse_op_log("") == []
        assert OperationManager._parse_op_log("   \n\n  ") == []

    def test_parse_realistic_output(self):
        text = (
            "0d76c1c221bd user@host now, lasted 13ms\n"
            "new empty commit\n"
            "args: jj new -m second\n"
            "\n"
            "4590b0888d6d user@host now, lasted 12ms\n"
            "describe commit 8990ccc60928\n"
            "args: jj describe -m 'first change'\n"
            "\n"
            "2d0032df3df2 user@host now, lasted 12ms\n"
            "add workspace 'default'\n"
            "\n"
            "000000000000 root()\n"
        )
        ops = OperationManager._parse_op_log(text)
        assert len(ops) == 4
        assert ops[0].id == "0d76c1c221bd"
        assert ops[0].description == "new empty commit"
        assert ops[1].description == "describe commit 8990ccc60928"
        assert ops[2].description == "add workspace 'default'"
        assert ops[3].id == "000000000000"


class TestOperationRestore:
    @pytest.mark.asyncio
    async def test_restore(self, om):
        mgr, mx = om
        mx.queue(stdout="")
        await mgr.restore("abc123")
        cmd = mx.calls[0]
        assert "operation" in cmd
        assert "restore" in cmd
        assert "abc123" in cmd


class TestOperationRevert:
    @pytest.mark.asyncio
    async def test_revert(self, om):
        mgr, mx = om
        mx.queue(stdout="")
        await mgr.revert("abc123")
        cmd = mx.calls[0]
        assert "operation" in cmd
        assert "undo" in cmd
        assert "abc123" in cmd
