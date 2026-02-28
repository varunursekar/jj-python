from __future__ import annotations

from ._runner import Runner
from .models import Bookmark


class BookmarkManager:
    """Manages jj bookmarks (repo.bookmark.*)."""

    def __init__(self, runner: Runner) -> None:
        self._runner = runner

    async def list(self, *, all_remotes: bool = False) -> list[Bookmark]:
        """List bookmarks."""
        args = ["bookmark", "list"]
        if all_remotes:
            args.append("--all-remotes")
        result = await self._runner.run(args)
        bookmarks: list[Bookmark] = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # Lines look like: "name: change_id commit_id" or "name (deleted)"
            # or "name@remote: ..."
            name = line.split(":")[0].strip()
            present = "(deleted)" not in line
            tracking = None
            if "@" in name:
                name_part, _, remote = name.partition("@")
                tracking = remote
                name = name_part
            bookmarks.append(Bookmark(name=name, present=present, tracking=tracking))
        return bookmarks

    async def create(self, name: str, *, revision: str | None = None) -> None:
        """Create a new bookmark."""
        args = ["bookmark", "create", name]
        if revision is not None:
            args.extend(["-r", revision])
        await self._runner.run(args)

    async def delete(self, *names: str) -> None:
        """Delete bookmarks."""
        args = ["bookmark", "delete"]
        args.extend(names)
        await self._runner.run(args)

    async def forget(self, *names: str) -> None:
        """Forget bookmarks (remove local and remote tracking)."""
        args = ["bookmark", "forget"]
        args.extend(names)
        await self._runner.run(args)

    async def move(self, name: str, *, to: str | None = None) -> None:
        """Move a bookmark to a different revision."""
        args = ["bookmark", "move", name]
        if to is not None:
            args.extend(["--to", to])
        await self._runner.run(args)

    async def set(self, name: str, *, revision: str | None = None) -> None:
        """Set a bookmark (create or move)."""
        args = ["bookmark", "set", name]
        if revision is not None:
            args.extend(["-r", revision])
        await self._runner.run(args)

    async def rename(self, old: str, new: str) -> None:
        """Rename a bookmark."""
        await self._runner.run(["bookmark", "rename", old, new])

    async def track(self, bookmark: str, *, remote: str = "origin") -> None:
        """Start tracking a remote bookmark."""
        await self._runner.run(["bookmark", "track", f"{bookmark}@{remote}"])

    async def untrack(self, bookmark: str, *, remote: str = "origin") -> None:
        """Stop tracking a remote bookmark."""
        await self._runner.run(["bookmark", "untrack", f"{bookmark}@{remote}"])
