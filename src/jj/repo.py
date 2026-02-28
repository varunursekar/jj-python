from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from ._executor import Executor
from ._parsing import CHANGE_LIST_TEMPLATE, CHANGE_TEMPLATE, parse_change, parse_changes
from ._runner import Runner
from .models import Change, DiffSummary


@dataclass(frozen=True)
class Status:
    """Working copy status: current change + diff summary."""

    working_copy: Change
    diff: DiffSummary


class Repo:
    """Main entry point for interacting with a jj repository."""

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        jj_path: str = "jj",
        executor: Executor | None = None,
    ) -> None:
        repo_path = Path(path) if path is not None else None
        self._runner = Runner(jj_path=jj_path, repo_path=repo_path, executor=executor)

        # Lazy imports to avoid circular dependencies
        from ._bookmark import BookmarkManager
        from ._git import GitManager
        from ._operation import OperationManager
        from ._workspace import WorkspaceManager

        self.bookmark = BookmarkManager(self._runner)
        self.git = GitManager(self._runner)
        self.workspace = WorkspaceManager(self._runner)
        self.op = OperationManager(self._runner)

    # -- Escape hatch -------------------------------------------------------

    async def run(
        self,
        args: list[str],
        *,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        """Run an arbitrary jj command and return the raw CompletedProcess."""
        return await self._runner.run(args, check=check)

    # -- Query commands -----------------------------------------------------

    async def log(
        self,
        *,
        revset: str = "@",
        limit: int | None = None,
    ) -> list[Change]:
        """Return changes matching a revset."""
        args = ["log", "--no-graph", "-T", CHANGE_LIST_TEMPLATE, "-r", revset]
        if limit is not None:
            args.extend(["-n", str(limit)])
        result = await self._runner.run(args)
        return parse_changes(result.stdout)

    async def show(self, rev: str = "@") -> Change:
        """Show a single change."""
        args = ["log", "--no-graph", "-T", CHANGE_TEMPLATE, "-r", rev, "-n", "1"]
        result = await self._runner.run(args)
        return parse_change(result.stdout)

    async def diff(
        self,
        *,
        revision: str | None = None,
        from_rev: str | None = None,
        to_rev: str | None = None,
    ) -> DiffSummary:
        """Return a parsed diff summary."""
        args = ["diff", "--summary"]
        if revision is not None:
            args.extend(["-r", revision])
        if from_rev is not None:
            args.extend(["--from", from_rev])
        if to_rev is not None:
            args.extend(["--to", to_rev])
        result = await self._runner.run(args)
        return DiffSummary.parse(result.stdout)

    async def diff_git(
        self,
        *,
        revision: str | None = None,
        from_rev: str | None = None,
        to_rev: str | None = None,
    ) -> str:
        """Return a raw git-format diff string."""
        args = ["diff", "--git"]
        if revision is not None:
            args.extend(["-r", revision])
        if from_rev is not None:
            args.extend(["--from", from_rev])
        if to_rev is not None:
            args.extend(["--to", to_rev])
        result = await self._runner.run(args)
        return result.stdout

    async def status(self) -> Status:
        """Return the working copy status (change metadata + diff)."""
        wc = await self.show("@")
        ds = await self.diff()
        return Status(working_copy=wc, diff=ds)

    async def file_list(self, *, revision: str | None = None) -> list[str]:
        """List tracked files."""
        args = ["file", "list"]
        if revision is not None:
            args.extend(["-r", revision])
        result = await self._runner.run(args)
        return [f for f in result.stdout.strip().splitlines() if f]

    # -- Mutation commands --------------------------------------------------

    async def new(
        self,
        *revisions: str,
        message: str | None = None,
        insert_before: bool = False,
        insert_after: bool = False,
    ) -> Change:
        """Create a new change."""
        args = ["new"]
        args.extend(revisions)
        if message is not None:
            args.extend(["-m", message])
        if insert_before:
            args.append("--insert-before")
        if insert_after:
            args.append("--insert-after")
        await self._runner.run(args)
        return await self.show("@")

    async def describe(
        self,
        revision: str = "@",
        *,
        message: str,
        reset_author: bool = False,
    ) -> Change:
        """Set the description of a change."""
        args = ["describe", revision, "-m", message]
        if reset_author:
            args.append("--reset-author")
        await self._runner.run(args)
        return await self.show(revision)

    async def commit(self, *, message: str) -> Change:
        """Finalize the working copy into a named commit and start a new change."""
        args = ["commit", "-m", message]
        await self._runner.run(args)
        return await self.show("@-")

    async def edit(self, revision: str) -> None:
        """Set the working copy to the given revision."""
        await self._runner.run(["edit", revision])

    async def squash(
        self,
        *,
        revision: str | None = None,
        into: str | None = None,
        message: str | None = None,
    ) -> None:
        """Squash a change into its parent (or into a specific revision)."""
        args = ["squash"]
        if revision is not None:
            args.extend(["-r", revision])
        if into is not None:
            args.extend(["--into", into])
        if message is not None:
            args.extend(["-m", message])
        await self._runner.run(args)

    async def split(
        self,
        *,
        revision: str | None = None,
        files: list[str],
    ) -> None:
        """Split a change by file paths (interactive split not supported)."""
        args = ["split"]
        if revision is not None:
            args.extend(["-r", revision])
        args.append("--")
        args.extend(files)
        await self._runner.run(args)

    async def rebase(
        self,
        *,
        revision: str | None = None,
        source: str | None = None,
        branch: str | None = None,
        destination: str,
    ) -> None:
        """Rebase revisions onto a destination."""
        args = ["rebase", "-d", destination]
        if revision is not None:
            args.extend(["-r", revision])
        if source is not None:
            args.extend(["-s", source])
        if branch is not None:
            args.extend(["-b", branch])
        await self._runner.run(args)

    async def abandon(self, *revisions: str) -> None:
        """Abandon one or more revisions."""
        args = ["abandon"]
        args.extend(revisions if revisions else ["@"])
        await self._runner.run(args)

    async def restore(
        self,
        *,
        revision: str | None = None,
        from_rev: str | None = None,
        to_rev: str | None = None,
    ) -> None:
        """Restore file contents from another revision."""
        args = ["restore"]
        if revision is not None:
            args.extend(["-r", revision])
        if from_rev is not None:
            args.extend(["--from", from_rev])
        if to_rev is not None:
            args.extend(["--to", to_rev])
        await self._runner.run(args)

    async def duplicate(self, *revisions: str) -> list[Change]:
        """Duplicate one or more revisions."""
        args = ["duplicate"]
        args.extend(revisions if revisions else ["@"])
        await self._runner.run(args)
        return await self.log(revset="latest(@-..)", limit=len(revisions) or 1)

    async def undo(self) -> None:
        """Undo the last operation."""
        await self._runner.run(["undo"])
