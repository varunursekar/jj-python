"""Tests for Runner behavior."""

from pathlib import Path
from unittest.mock import patch

import pytest

from jj._runner import Runner
from jj.errors import JJCommandError, JJNotFoundError, JJRepoNotFoundError

from .conftest import MockExecutor, make_runner


class TestRunnerInit:
    def test_raises_not_found_when_binary_missing(self):
        with patch("jj._runner.shutil.which", return_value=None):
            with pytest.raises(JJNotFoundError) as exc_info:
                Runner(jj_path="jj")
            assert exc_info.value.jj_path == "jj"

    def test_raises_not_found_custom_path(self):
        with patch("jj._runner.shutil.which", return_value=None):
            with pytest.raises(JJNotFoundError) as exc_info:
                Runner(jj_path="/nonexistent/jj")
            assert exc_info.value.jj_path == "/nonexistent/jj"

    def test_succeeds_when_binary_found(self):
        mock = MockExecutor()
        runner = make_runner(mock)
        assert runner.jj_path == "jj"


class TestRunnerCommand:
    @pytest.mark.asyncio
    async def test_builds_correct_base_command(self):
        mock = MockExecutor()
        mock.queue(stdout="ok")
        runner = make_runner(mock)
        await runner.run(["log"])
        assert mock.calls == [["jj", "--no-pager", "--color", "never", "log"]]

    @pytest.mark.asyncio
    async def test_appends_repository_when_set(self):
        mock = MockExecutor()
        mock.queue(stdout="ok")
        runner = make_runner(mock, repo_path=Path("/my/repo"))
        await runner.run(["status"])
        cmd = mock.calls[0]
        assert "--repository" in cmd
        idx = cmd.index("--repository")
        assert cmd[idx + 1] == "/my/repo"

    @pytest.mark.asyncio
    async def test_no_repository_flag_when_none(self):
        mock = MockExecutor()
        mock.queue(stdout="ok")
        runner = make_runner(mock)
        await runner.run(["log"])
        assert "--repository" not in mock.calls[0]

    @pytest.mark.asyncio
    async def test_extends_with_args(self):
        mock = MockExecutor()
        mock.queue(stdout="")
        runner = make_runner(mock)
        await runner.run(["log", "--no-graph", "-r", "@"])
        cmd = mock.calls[0]
        assert cmd[-4:] == ["log", "--no-graph", "-r", "@"]


class TestRunnerCheck:
    @pytest.mark.asyncio
    async def test_check_true_raises_on_nonzero(self):
        mock = MockExecutor()
        mock.queue(returncode=1, stderr="error msg")
        runner = make_runner(mock)
        with pytest.raises(JJCommandError) as exc_info:
            await runner.run(["bad-cmd"], check=True)
        assert exc_info.value.exit_code == 1
        assert exc_info.value.stderr == "error msg"

    @pytest.mark.asyncio
    async def test_check_false_returns_result_on_nonzero(self):
        mock = MockExecutor()
        mock.queue(returncode=1, stderr="err")
        runner = make_runner(mock)
        result = await runner.run(["bad-cmd"], check=False)
        assert result.returncode == 1

    @pytest.mark.asyncio
    async def test_check_true_is_default(self):
        mock = MockExecutor()
        mock.queue(returncode=1, stderr="fail")
        runner = make_runner(mock)
        with pytest.raises(JJCommandError):
            await runner.run(["fail"])


class TestRunnerRepoNotFound:
    @pytest.mark.asyncio
    async def test_detects_no_repo_hint(self):
        mock = MockExecutor()
        mock.queue(returncode=1, stderr="There is no jj repo in /some/path")
        runner = make_runner(mock)
        with pytest.raises(JJRepoNotFoundError):
            await runner.run(["log"])

    @pytest.mark.asyncio
    async def test_detects_no_repo_found(self):
        mock = MockExecutor()
        mock.queue(returncode=1, stderr="No repo found at this location")
        runner = make_runner(mock)
        with pytest.raises(JJRepoNotFoundError):
            await runner.run(["log"])

    @pytest.mark.asyncio
    async def test_detects_not_valid_jj_repo(self):
        mock = MockExecutor()
        mock.queue(returncode=1, stderr="/foo is not a valid jj repo")
        runner = make_runner(mock)
        with pytest.raises(JJRepoNotFoundError):
            await runner.run(["log"])

    @pytest.mark.asyncio
    async def test_generic_error_when_no_hint(self):
        mock = MockExecutor()
        mock.queue(returncode=1, stderr="something else went wrong")
        runner = make_runner(mock)
        with pytest.raises(JJCommandError) as exc_info:
            await runner.run(["log"])
        assert not isinstance(exc_info.value, JJRepoNotFoundError)
