from __future__ import annotations

import asyncio
import subprocess


class DockerExecutor:
    """Executor that runs jj commands inside a Docker container.

    Can either attach to an existing container or start one from an image.

    Attach to a running container::

        executor = DockerExecutor(container="my-jj-sandbox", workdir="/repo")

    Start a new container from an image::

        executor = await DockerExecutor.start(
            image="my-jj-image",
            workdir="/repo",
            volumes={"/host/repo": "/repo"},
        )
        # ... use executor ...
        await executor.stop()

    Use as an async context manager (auto-stops)::

        async with await DockerExecutor.start(image="my-jj-image") as executor:
            repo = Repo("/repo", executor=executor)
            changes = await repo.log()
    """

    def __init__(
        self,
        container: str,
        *,
        workdir: str | None = None,
        user: str | None = None,
        env: dict[str, str] | None = None,
        docker_path: str = "docker",
        _owns_container: bool = False,
    ) -> None:
        self.container = container
        self.workdir = workdir
        self.user = user
        self.env = env or {}
        self.docker_path = docker_path
        self._owns_container = _owns_container

    @classmethod
    async def start(
        cls,
        image: str,
        *,
        workdir: str | None = None,
        user: str | None = None,
        env: dict[str, str] | None = None,
        volumes: dict[str, str] | None = None,
        ports: dict[int, int] | None = None,
        docker_path: str = "docker",
    ) -> DockerExecutor:
        """Start a new container from *image* and return an executor attached to it."""
        cmd = [docker_path, "run", "-d", "--rm"]
        if workdir is not None:
            cmd.extend(["-w", workdir])
        if user is not None:
            cmd.extend(["-u", user])
        for key, value in (env or {}).items():
            cmd.extend(["-e", f"{key}={value}"])
        for host_path, container_path in (volumes or {}).items():
            cmd.extend(["-v", f"{host_path}:{container_path}"])
        for host_port, container_port in (ports or {}).items():
            cmd.extend(["-p", f"{host_port}:{container_port}"])
        # Keep the container alive with a long sleep
        cmd.extend([image, "sleep", "infinity"])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(
                f"Failed to start container (exit {proc.returncode}): {stderr.decode()}"
            )

        container_id = stdout.decode().strip()
        return cls(
            container=container_id,
            workdir=workdir,
            user=user,
            env=env,
            docker_path=docker_path,
            _owns_container=True,
        )

    async def stop(self) -> None:
        """Stop and remove the container (only if we started it)."""
        if not self._owns_container:
            return
        proc = await asyncio.create_subprocess_exec(
            self.docker_path, "stop", self.container,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        self._owns_container = False

    async def execute(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        docker_cmd = [self.docker_path, "exec"]
        if self.workdir is not None:
            docker_cmd.extend(["-w", self.workdir])
        if self.user is not None:
            docker_cmd.extend(["-u", self.user])
        for key, value in self.env.items():
            docker_cmd.extend(["-e", f"{key}={value}"])
        docker_cmd.append(self.container)
        docker_cmd.extend(cmd)

        proc = await asyncio.create_subprocess_exec(
            *docker_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout_bytes, stderr_bytes = await proc.communicate()
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=proc.returncode or 0,
            stdout=stdout_bytes.decode(),
            stderr=stderr_bytes.decode(),
        )

    async def __aenter__(self) -> DockerExecutor:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.stop()
