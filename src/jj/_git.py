from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

from ._executor import Executor
from ._runner import Runner

if TYPE_CHECKING:
    from .repo import Repo


class GitManager:
    """Manages jj git operations (repo.git.*)."""

    def __init__(self, runner: Runner) -> None:
        self._runner = runner

    async def push(
        self,
        *,
        remote: str | None = None,
        bookmark: str | None = None,
        all_bookmarks: bool = False,
        change: str | None = None,
    ) -> str:
        """Push to a git remote. Returns command output."""
        args = ["git", "push"]
        if remote is not None:
            args.extend(["--remote", remote])
        if bookmark is not None:
            args.extend(["-b", bookmark])
        if all_bookmarks:
            args.append("--all")
        if change is not None:
            args.extend(["-c", change])
        result = await self._runner.run(args)
        return result.stderr + result.stdout

    async def fetch(
        self,
        *,
        remote: str | None = None,
        all_remotes: bool = False,
    ) -> str:
        """Fetch from a git remote. Returns command output."""
        args = ["git", "fetch"]
        if remote is not None:
            args.extend(["--remote", remote])
        if all_remotes:
            args.append("--all-remotes")
        result = await self._runner.run(args)
        return result.stderr + result.stdout

    @staticmethod
    async def clone(
        url: str,
        destination: str | Path | None = None,
        *,
        jj_path: str = "jj",
        executor: Executor | None = None,
    ) -> Repo:
        """Clone a git repository. Returns a new Repo pointed at the clone."""
        from .repo import Repo

        runner = Runner(jj_path=jj_path, executor=executor)
        args = ["git", "clone", url]
        if destination is not None:
            args.append(str(destination))
        await runner.run(args)

        if destination is not None:
            clone_path = Path(destination)
        else:
            name = url.rstrip("/").rsplit("/", 1)[-1]
            if name.endswith(".git"):
                name = name[:-4]
            clone_path = Path(name)

        return Repo(clone_path, jj_path=jj_path, executor=executor)

    async def remote_add(self, name: str, url: str) -> None:
        """Add a git remote."""
        await self._runner.run(["git", "remote", "add", name, url])

    async def remote_remove(self, name: str) -> None:
        """Remove a git remote."""
        await self._runner.run(["git", "remote", "remove", name])

    async def remote_rename(self, old: str, new: str) -> None:
        """Rename a git remote."""
        await self._runner.run(["git", "remote", "rename", old, new])

    async def remote_list(self) -> dict[str, str]:
        """List git remotes. Returns {name: url}."""
        result = await self._runner.run(["git", "remote", "list"])
        remotes: dict[str, str] = {}
        for line in result.stdout.strip().splitlines():
            if not line.strip():
                continue
            parts = line.split(None, 1)
            if len(parts) == 2:
                remotes[parts[0]] = parts[1]
            elif len(parts) == 1:
                remotes[parts[0]] = ""
        return remotes

    async def remote_set_url(self, name: str, url: str) -> None:
        """Set the URL of a git remote."""
        await self._runner.run(["git", "remote", "set-url", name, url])

    async def export(self) -> None:
        """Export jj refs to the underlying git repo."""
        await self._runner.run(["git", "export"])

    async def import_(self) -> None:
        """Import git refs into jj."""
        await self._runner.run(["git", "import"])

    # -- Bundle operations (via underlying git repo) ------------------------

    async def _workspace_root(self) -> str:
        result = await self._runner.run(["workspace", "root"])
        return result.stdout.strip()

    async def _git_cmd(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        """Run a raw git command against the underlying git repo."""
        root = await self._workspace_root()
        return await self._runner.executor.execute(["git", "-C", root, *args])

    async def bundle_create(
        self,
        path: str,
        *,
        refs: list[str] | None = None,
    ) -> str:
        """Create a git bundle from the underlying repo.

        Exports jj refs to git first, then runs ``git bundle create``.
        If *refs* is not given, bundles ``--all``.

        Returns the bundle file path.
        """
        await self.export()
        args = ["bundle", "create", path]
        if refs:
            args.extend(refs)
        else:
            args.append("--all")
        result = await self._git_cmd(args)
        if result.returncode != 0:
            from .errors import JJCommandError

            raise JJCommandError(
                ["git", *args], result.returncode, result.stderr.strip()
            )
        return path

    async def bundle_unbundle(
        self, path: str, *, refspec: str = "+refs/*:refs/*"
    ) -> None:
        """Fetch from a git bundle into the underlying repo, then import into jj.

        Uses ``git fetch <bundle> <refspec>`` to unpack objects *and* create refs.
        The default *refspec* maps all bundle refs into the local repo.
        """
        result = await self._git_cmd(["fetch", path, refspec])
        if result.returncode != 0:
            from .errors import JJCommandError

            raise JJCommandError(
                ["git", "fetch", path, refspec],
                result.returncode,
                result.stderr.strip(),
            )
        await self.import_()

    async def bundle_verify(self, path: str) -> str:
        """Verify a git bundle. Returns the verification output."""
        result = await self._git_cmd(["bundle", "verify", path])
        if result.returncode != 0:
            from .errors import JJCommandError

            raise JJCommandError(
                ["git", "bundle", "verify", path],
                result.returncode,
                result.stderr.strip(),
            )
        return (result.stdout + result.stderr).strip()
