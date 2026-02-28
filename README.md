# jj — Python API for Jujutsu

> **Experimental** — This library is under active development. APIs may change without notice.

A Pythonic async wrapper over the [jj](https://github.com/jj-vcs/jj) CLI for scripting and automation, similar to how GitPython wraps git.

## Install

```bash
uv add jj --path .
# or
pip install .
```

Requires Python 3.11+ and `jj` on your PATH.

## Quick start

```python
import asyncio
from jj import Repo

async def main():
    repo = Repo("/path/to/repo")

    # Query
    changes = await repo.log(revset="@")
    status = await repo.status()
    files = await repo.file_list()

    # Mutate
    await repo.new(message="new change")
    await repo.describe(message="updated description")
    await repo.commit(message="finalize")

asyncio.run(main())
```

## Sub-managers

### Bookmarks (`repo.bookmark`)

```python
await repo.bookmark.create("feature-x")
await repo.bookmark.list()
await repo.bookmark.move("feature-x", to="@-")
await repo.bookmark.delete("feature-x")
```

### Git (`repo.git`)

```python
await repo.git.fetch()
await repo.git.push(bookmark="main")
await repo.git.remote_list()

# Bundle support (via underlying git repo)
await repo.git.bundle_create("/tmp/repo.bundle")
await repo.git.bundle_unbundle("/tmp/repo.bundle")
```

### Workspaces (`repo.workspace`)

```python
await repo.workspace.add("/path/to/ws", name="secondary")
workspaces = await repo.workspace.list()
root = await repo.workspace.root()
```

### Operations (`repo.op`)

```python
ops = await repo.op.log(limit=5)
await repo.op.restore(ops[0].id)
```

## Sandbox execution

All commands run through a pluggable `Executor` protocol. The default `LocalExecutor` uses local subprocess; swap in `DockerExecutor` to run jj inside a container.

```python
from jj import Repo, DockerExecutor

# Attach to a running container
executor = DockerExecutor(container="my-sandbox", workdir="/repo")
repo = Repo("/repo", executor=executor)

# Or start a new container from an image
async with await DockerExecutor.start(
    image="my-jj-image",
    workdir="/repo",
    volumes={"/host/repo": "/repo"},
) as executor:
    repo = Repo("/repo", executor=executor)
    changes = await repo.log()
```

### Custom executor

Implement the `Executor` protocol to run commands anywhere:

```python
import subprocess
from jj import Repo, Executor

class SSHExecutor:
    def __init__(self, host: str):
        self.host = host

    async def execute(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        # wrap cmd in ssh, nsjail, etc.
        ...

repo = Repo("/remote/path", executor=SSHExecutor("server"))
```

## Error handling

```python
from jj import Repo, JJRepoNotFoundError, JJNotFoundError

# Binary not found — raised at construction
try:
    Repo(jj_path="/bad/path")
except JJNotFoundError:
    ...

# Repo not found — raised on first command
try:
    await Repo("/nonexistent").log()
except JJRepoNotFoundError:
    ...
```

## Escape hatch

Run any jj command directly:

```python
result = await repo.run(["version"])
print(result.stdout)
```

## Development

```bash
uv sync          # install deps + dev deps
uv run pytest -v # run all tests
```

The test suite includes both **unit tests** (using a mock executor, no jj required) and **integration tests** (running real jj commands against temp repos). Integration tests are automatically skipped if `jj` is not installed.
