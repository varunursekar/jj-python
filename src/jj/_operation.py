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
        """Parse ``jj operation log --no-graph`` output.

        Real format (each entry separated by blank lines)::

            <id> <user> <time-description>
            <description>
            args: <command args>          ← optional, absent for root op

        The root operation looks like::

            000000000000 root()
        """
        operations: list[Operation] = []
        # Split into blocks separated by blank lines
        blocks: list[list[str]] = []
        current_block: list[str] = []
        for line in output.splitlines():
            if not line.strip():
                if current_block:
                    blocks.append(current_block)
                    current_block = []
            else:
                current_block.append(line)
        if current_block:
            blocks.append(current_block)

        for block in blocks:
            if not block:
                continue
            # First line: "<id> <user> <time>" (3+ space-separated tokens)
            header = block[0]
            parts = header.split(None, 2)
            op_id = parts[0] if len(parts) >= 1 else ""
            user = parts[1] if len(parts) >= 2 else ""
            time = parts[2] if len(parts) >= 3 else ""
            # Remaining lines: description, then optionally "args: ..."
            desc_lines: list[str] = []
            tags = ""
            for line in block[1:]:
                if line.startswith("args: "):
                    tags = line[6:]  # store the args in tags for reference
                else:
                    desc_lines.append(line)
            description = "\n".join(desc_lines)

            operations.append(
                Operation(
                    id=op_id,
                    description=description,
                    time=time,
                    user=user,
                    tags=tags,
                )
            )

        return operations
