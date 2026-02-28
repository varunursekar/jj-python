from __future__ import annotations


class JJError(Exception):
    """Base exception for all jj errors."""


class JJNotFoundError(JJError):
    """Raised when the jj binary is not found on PATH."""

    def __init__(self, jj_path: str = "jj") -> None:
        super().__init__(
            f"Could not find jj binary at {jj_path!r}. "
            "Is jj installed and on your PATH?"
        )
        self.jj_path = jj_path


class JJCommandError(JJError):
    """Raised when a jj command exits with a non-zero status."""

    def __init__(
        self,
        command: list[str],
        exit_code: int,
        stderr: str,
    ) -> None:
        super().__init__(
            f"jj command failed (exit {exit_code}): {' '.join(command)}\n{stderr}"
        )
        self.command = command
        self.exit_code = exit_code
        self.stderr = stderr


class JJRepoNotFoundError(JJCommandError):
    """Raised when jj cannot find a repository at the given path."""
