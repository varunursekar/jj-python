from __future__ import annotations

import asyncio
import subprocess
from typing import Protocol, runtime_checkable


@runtime_checkable
class Executor(Protocol):
    """Protocol for executing shell commands.

    Implement this to run jj commands in a sandbox (Docker, nsjail, etc.)
    instead of directly via local subprocess.
    """

    async def execute(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        """Execute *cmd* and return a CompletedProcess with captured stdout/stderr."""
        ...


class LocalExecutor:
    """Default executor — runs commands via local async subprocess."""

    async def execute(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=proc.returncode or 0,
            stdout=stdout_bytes.decode(),
            stderr=stderr_bytes.decode(),
        )
