from __future__ import annotations

from ._runner import Runner


class WorkspaceManager:
    """Manages jj workspaces (repo.workspace.*)."""

    def __init__(self, runner: Runner) -> None:
        self._runner = runner

    async def add(self, path: str, *, name: str | None = None) -> None:
        """Add a new workspace."""
        args = ["workspace", "add", path]
        if name is not None:
            args.extend(["--name", name])
        await self._runner.run(args)

    async def forget(self, *names: str) -> None:
        """Forget workspaces."""
        args = ["workspace", "forget"]
        args.extend(names)
        await self._runner.run(args)

    async def list(self) -> list[str]:
        """List workspaces. Returns workspace names."""
        result = await self._runner.run(["workspace", "list"])
        names: list[str] = []
        for line in result.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # Format: "name: change_id (description)"
            name = line.split(":")[0].strip()
            names.append(name)
        return names

    async def root(self) -> str:
        """Return the root path of the current workspace."""
        result = await self._runner.run(["workspace", "root"])
        return result.stdout.strip()

    async def update_stale(self) -> None:
        """Update a stale workspace."""
        await self._runner.run(["workspace", "update-stale"])
