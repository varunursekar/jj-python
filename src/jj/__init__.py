"""Pythonic wrapper over the jj CLI for scripting and automation."""

from ._docker import DockerExecutor
from ._executor import Executor, LocalExecutor
from .errors import JJCommandError, JJError, JJNotFoundError, JJRepoNotFoundError
from .models import Bookmark, Change, DiffEntry, DiffSummary, Operation, Signature
from .repo import Repo, Status

__all__ = [
    "Repo",
    "Status",
    "Change",
    "Signature",
    "Bookmark",
    "DiffEntry",
    "DiffSummary",
    "Operation",
    "Executor",
    "LocalExecutor",
    "DockerExecutor",
    "JJError",
    "JJCommandError",
    "JJNotFoundError",
    "JJRepoNotFoundError",
]
