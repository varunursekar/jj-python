"""Tests for DockerExecutor."""

from unittest.mock import AsyncMock, patch

import pytest

from jj._docker import DockerExecutor

_PATCH_TARGET = "jj._docker.asyncio.create_subprocess_exec"


class TestDockerExecute:
    @pytest.mark.asyncio
    async def test_execute_wraps_command(self):
        executor = DockerExecutor(container="test-container")
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"output", b"")
        mock_proc.returncode = 0

        with patch(_PATCH_TARGET, return_value=mock_proc) as mock_exec:
            result = await executor.execute(["jj", "log"])

        # Should wrap in docker exec
        call_args = mock_exec.call_args[0]
        assert call_args[0] == "docker"
        assert call_args[1] == "exec"
        assert "test-container" in call_args
        assert "jj" in call_args
        assert "log" in call_args

        # Result should report the original cmd, not the docker cmd
        assert result.args == ["jj", "log"]
        assert result.stdout == "output"
        assert result.returncode == 0

    @pytest.mark.asyncio
    async def test_execute_with_workdir(self):
        executor = DockerExecutor(container="c1", workdir="/repo")
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0

        with patch(_PATCH_TARGET, return_value=mock_proc) as mock_exec:
            await executor.execute(["jj", "status"])

        call_args = mock_exec.call_args[0]
        assert "-w" in call_args
        idx = call_args.index("-w")
        assert call_args[idx + 1] == "/repo"

    @pytest.mark.asyncio
    async def test_execute_with_user(self):
        executor = DockerExecutor(container="c1", user="nobody")
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0

        with patch(_PATCH_TARGET, return_value=mock_proc) as mock_exec:
            await executor.execute(["jj", "log"])

        call_args = mock_exec.call_args[0]
        assert "-u" in call_args
        idx = call_args.index("-u")
        assert call_args[idx + 1] == "nobody"

    @pytest.mark.asyncio
    async def test_execute_with_env(self):
        executor = DockerExecutor(container="c1", env={"FOO": "bar"})
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0

        with patch(_PATCH_TARGET, return_value=mock_proc) as mock_exec:
            await executor.execute(["jj", "log"])

        call_args = mock_exec.call_args[0]
        assert "-e" in call_args
        idx = call_args.index("-e")
        assert call_args[idx + 1] == "FOO=bar"


class TestDockerStart:
    @pytest.mark.asyncio
    async def test_start_builds_correct_command(self):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"container123\n", b"")
        mock_proc.returncode = 0

        with patch(_PATCH_TARGET, return_value=mock_proc) as mock_exec:
            executor = await DockerExecutor.start(
                image="my-image",
                workdir="/repo",
                user="jjuser",
                env={"KEY": "val"},
                volumes={"/host": "/container"},
                ports={8080: 80},
            )

        call_args = mock_exec.call_args[0]
        assert call_args[0] == "docker"
        assert "run" in call_args
        assert "-d" in call_args
        assert "--rm" in call_args
        assert "-w" in call_args
        assert "-u" in call_args
        assert "my-image" in call_args
        assert "sleep" in call_args
        assert "infinity" in call_args

        assert executor.container == "container123"
        assert executor._owns_container is True

    @pytest.mark.asyncio
    async def test_start_error(self):
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"error starting")
        mock_proc.returncode = 1

        with (
            patch(_PATCH_TARGET, return_value=mock_proc),
            pytest.raises(RuntimeError, match="Failed to start container"),
        ):
            await DockerExecutor.start(image="bad-image")


class TestDockerStop:
    @pytest.mark.asyncio
    async def test_stop_when_owns_container(self):
        executor = DockerExecutor(container="c1", _owns_container=True)
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0

        with patch(_PATCH_TARGET, return_value=mock_proc) as mock_exec:
            await executor.stop()

        call_args = mock_exec.call_args[0]
        assert "docker" in call_args
        assert "stop" in call_args
        assert "c1" in call_args
        assert executor._owns_container is False

    @pytest.mark.asyncio
    async def test_stop_noop_when_not_owned(self):
        executor = DockerExecutor(container="c1", _owns_container=False)
        with patch(_PATCH_TARGET) as mock_exec:
            await executor.stop()
        mock_exec.assert_not_called()


class TestDockerContextManager:
    @pytest.mark.asyncio
    async def test_aenter_returns_self(self):
        executor = DockerExecutor(container="c1")
        result = await executor.__aenter__()
        assert result is executor

    @pytest.mark.asyncio
    async def test_aexit_calls_stop(self):
        executor = DockerExecutor(container="c1", _owns_container=True)
        mock_proc = AsyncMock()
        mock_proc.communicate.return_value = (b"", b"")
        mock_proc.returncode = 0

        with patch(_PATCH_TARGET, return_value=mock_proc):
            async with executor:
                pass
        # After exiting, should have been stopped
        assert executor._owns_container is False
