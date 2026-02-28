from __future__ import annotations

from ._runner import Runner
from .models import Operation


class OperationManager:
    """Manages jj operations (repo.op.*)."""

    def __init__(self, runner: Runner) -> None:
        self._runner = runner

    async def log(self, *, limit: int | None = None) -> list[Operation]:
        """List operations."""
        args = ["operation", "log", "--no-graph"]
        if limit is not None:
            args.extend(["-n", str(limit)])
        result = await self._runner.run(args)
        return self._parse_op_log(result.stdout)

    async def restore(self, operation_id: str) -> None:
        """Restore to a previous operation."""
        await self._runner.run(["operation", "restore", operation_id])

    async def revert(self, operation_id: str) -> None:
        """Revert an operation (inverse patch)."""
        await self._runner.run(["operation", "undo", operation_id])

    @staticmethod
    def _parse_op_log(output: str) -> list[Operation]:
        """Parse operation log text output into Operation objects."""
        operations: list[Operation] = []
        current: dict[str, str] = {}

        for line in output.splitlines():
            if not line.strip():
                if current:
                    operations.append(Operation(
                        id=current.get("id", ""),
                        description=current.get("description", ""),
                        time=current.get("time", ""),
                        user=current.get("user", ""),
                        tags=current.get("tags", ""),
                    ))
                    current = {}
                continue

            for key in ("id", "description", "time", "user", "tags"):
                if line.strip().lower().startswith(key):
                    _, _, value = line.partition(":")
                    current[key] = value.strip()
                    break

        if current:
            operations.append(Operation(
                id=current.get("id", ""),
                description=current.get("description", ""),
                time=current.get("time", ""),
                user=current.get("user", ""),
                tags=current.get("tags", ""),
            ))

        return operations
