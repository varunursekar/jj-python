from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ._executor import Executor, LocalExecutor
from .errors import JJCommandError, JJNotFoundError, JJRepoNotFoundError

_REPO_NOT_FOUND_HINTS = (
    "There is no jj repo",
    "No repo found",
    "is not a valid jj repo",
)


class Runner:
    """Low-level async wrapper for jj commands."""

    def __init__(
        self,
        jj_path: str = "jj",
        repo_path: Path | None = None,
        executor: Executor | None = None,
    ) -> None:
        self.jj_path = jj_path
        self.repo_path = repo_path
        self.executor = executor or LocalExecutor()
        if not shutil.which(jj_path):
            raise JJNotFoundError(jj_path)

    async def run(
        self,
        args: list[str],
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        cmd = [self.jj_path, "--no-pager", "--color", "never"]
        if self.repo_path is not None:
            cmd.extend(["--repository", str(self.repo_path)])
        cmd.extend(args)

        result = await self.executor.execute(cmd)

        if check and result.returncode != 0:
            stderr = result.stderr.strip()
            if any(hint in stderr for hint in _REPO_NOT_FOUND_HINTS):
                raise JJRepoNotFoundError(cmd, result.returncode, stderr)
            raise JJCommandError(cmd, result.returncode, stderr)

        return result
