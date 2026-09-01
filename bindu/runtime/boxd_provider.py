"""BoxdRuntimeProvider — runs a bindu agent inside a boxd microVM.

Two modes:

- **A2** (default): ship local source via tar+gzip, install deps in the VM,
  exec the agent script directly.
- **A1**: provide an ``image`` field; boxd creates the VM from that image
  and the image's ``CMD`` is the entry point. No source ship.

The host's role ends after the agent is healthy. A2A clients then talk
directly to the VM's public URL.

Targets the boxd 0.2.x SDK: a flat ``AsyncBoxd`` client with
``machines.<verb>(id, ...)`` namespaces; ``Machine`` records are plain data.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Literal

import httpx

from bindu.runtime.base import RuntimeHandle, RuntimeProvider, register_provider
from bindu.runtime.config import RuntimeConfig
from bindu.runtime.source_packager import build_tarball, find_project_root
from bindu.utils.logging import get_logger

logger = get_logger(__name__)

# Bindu's default HTTP port. The machine's default proxy route is pointed at
# this port after create/reuse, so the agent's public URL routes correctly.
BINDU_DEFAULT_PORT = 3773

# Where we stage the user's source inside the VM. Must be writable by the
# default VM user (``boxd``); ``/app`` requires sudo on stock boxd images.
APP_DIR = "/home/boxd/app"

# Where we stage the host's bindu source when ``bindu_version == "local"``.
BINDU_SRC_DIR = "/home/boxd/bindu_source"

# Where the in-VM agent's stdout/stderr go. Streamed back to the host on
# demand via ``stream_logs`` (using ``tail -F`` over ``machines.stream_exec``;
# ``machines.logs`` is the VM console, which a detached nohup'd agent
# never writes to).
AGENT_LOG_PATH = "/tmp/bindu-agent.log"  # nosec B108 — single-tenant VM
AGENT_PID_PATH = "/tmp/bindu-agent.pid"  # nosec B108 — single-tenant VM

# Repo paths excluded when shipping the host's bindu source to a VM:
# nothing here is needed by ``pip install -e .`` for the Python package.
# Keeping the tarball small avoids hitting boxd's gRPC message size limit.
_BINDU_SHIP_EXCLUDES = (
    "assets/",
    "examples/",
    "docs/",
    "tests/",
    "gateway/",
    "sdks/",
    "i18n/",
    "bugs/",
    "release-notes/",
    "scripts/",
    ".agents/",
    "alembic/",
    ".github/",
    ".vscode/",
    "inbox/",
)

_VM_READY_TIMEOUT = 60.0
_HEALTH_TIMEOUT = 60.0
_POLL_INTERVAL = 1.0


def _make_client(**kwargs: Any):
    """Construct an AsyncBoxd client. Indirection so tests can patch."""
    from boxd import AsyncBoxd

    return AsyncBoxd(**kwargs)


async def _poll_until(
    probe: Callable[[], Awaitable[bool]],
    *,
    timeout: float,
    interval: float = _POLL_INTERVAL,
    error_msg: str,
) -> None:
    """Call ``probe`` repeatedly until it returns True or ``timeout`` elapses."""
    loop = asyncio.get_event_loop()
    deadline = loop.time() + timeout
    while loop.time() < deadline:
        try:
            if await probe():
                return
        except Exception:
            pass
        await asyncio.sleep(interval)
    raise TimeoutError(error_msg)


async def _exec_or_raise(
    client: Any,
    machine_id: str,
    *cmd: str,
    env: dict[str, str] | None = None,
    error: str,
) -> Any:
    """Run a command in the VM and raise if it exits non-zero."""
    result = await client.machines.exec(machine_id, list(cmd), env=env)
    if getattr(result, "exit_code", 0) != 0:
        stderr = getattr(result, "stderr", "")
        raise RuntimeError(f"{error}: {stderr}")
    return result


async def _get_machine(client: Any, name: str) -> Any | None:
    """Look up a machine by name; ``None`` when it doesn't exist.

    ``machines.get`` resolves a name in the account's default org context
    only, which misses machines living in another organization (observed
    with org-fenced API keys: ``get(name)`` raises NotFound while ``list``
    shows the machine). Fall back to an exact-name scan of ``list()``
    before concluding the machine is gone — creating over a name that
    actually exists fails with ConflictError, and a skipped teardown
    leaves the VM running (and billing) forever.
    """
    from boxd import NotFoundError

    try:
        return await client.machines.get(name)
    except NotFoundError:
        for machine in await client.machines.list():
            if machine.name == name:
                return machine
        return None


async def _upload_file(client: Any, machine_id: str, blob: bytes, dest: str) -> None:
    """Upload ``blob`` to ``dest`` and verify the confirmed byte count.

    boxd 0.2.x's ``files.upload`` streams in chunks and returns the number
    of bytes the machine confirmed it wrote — a mismatch means the artifact
    in the VM is corrupt, so fail the deploy rather than proceed.
    """
    written = await client.machines.files.upload(machine_id, dest, blob)
    if written != len(blob):
        raise RuntimeError(
            f"upload to {dest} incomplete: machine confirmed {written} of "
            f"{len(blob)} bytes"
        )


class BoxdRuntimeProvider(RuntimeProvider):
    """RuntimeProvider that runs the agent inside a boxd microVM."""

    async def _resolve_vm(self, client: Any, name: str, config: RuntimeConfig) -> Any:
        """Get or create the machine for this agent (idempotent by name).

        A reused machine may have been paused/hibernated/stopped since the
        last deploy (``on_exit='suspend'`` is the default); the 0.2.x SDK
        never resumes implicitly, so bring it back explicitly here.
        """
        machine = await _get_machine(client, name)
        if machine is None:
            # Sizing keys are passed only when explicitly configured: boxd
            # 0.2.x machines come in fixed vCPU/memory pairs with an org
            # default, and the server refuses per-machine disk sizing.
            create_kwargs: dict[str, Any] = {
                "auto_suspend_timeout": config.auto_suspend,
            }
            if config.vcpu is not None:
                create_kwargs["vcpu"] = config.vcpu
            if config.memory is not None:
                create_kwargs["memory"] = config.memory
            if config.disk is not None:
                create_kwargs["disk"] = config.disk
            if config.image:
                create_kwargs["image"] = config.image
            return await client.machines.create(name, **create_kwargs)

        if machine.status == "suspended":
            await client.machines.resume(machine.id)
        elif machine.status == "hibernated":
            await client.machines.wake(machine.id)
        elif machine.status == "stopped":
            await client.machines.start(machine.id)
        return machine

    async def _ship_source(
        self, client: Any, machine_id: str, source_dir: Path
    ) -> None:
        """Tar+gzip ``source_dir``, upload, extract to ``APP_DIR``."""
        blob = build_tarball(source_dir)
        # /tmp inside the VM is fine: the VM is single-tenant, the host is the
        # only writer, and the file is consumed immediately by the next exec.
        await _upload_file(client, machine_id, blob, "/tmp/source.tar.gz")  # nosec B108
        await _exec_or_raise(
            client,
            machine_id,
            "sh",
            "-c",
            f"mkdir -p {APP_DIR} && tar xzf /tmp/source.tar.gz -C {APP_DIR}",
            error=f"failed to extract source to {APP_DIR}",
        )

    async def _ship_bindu_source(self, client: Any, machine_id: str) -> None:
        """Tar the host's bindu source tree, ship to ``BINDU_SRC_DIR``.

        Used by ``bindu_version == "local"``: lets the VM run the same bindu
        as the host, useful for testing pre-publication branches and for
        users running a patched bindu.

        The bindu repo includes ~16 MB of comms UI / assets / docs that the
        Python package doesn't need at runtime; we exclude them to stay well
        under boxd's per-message gRPC upload limit.
        """
        import bindu as _bindu

        host_root = find_project_root(Path(_bindu.__file__).parent)
        if not (host_root / "pyproject.toml").exists():
            raise RuntimeError(
                "--bindu-version=local requires bindu installed from a source "
                f"checkout; no pyproject.toml found at or above {host_root}"
            )
        blob = build_tarball(host_root, extra_ignores=_BINDU_SHIP_EXCLUDES)
        await _upload_file(
            client,
            machine_id,
            blob,
            "/tmp/bindu-source.tar.gz",  # nosec B108
        )
        await _exec_or_raise(
            client,
            machine_id,
            "sh",
            "-c",
            f"mkdir -p {BINDU_SRC_DIR} && "
            f"tar xzf /tmp/bindu-source.tar.gz -C {BINDU_SRC_DIR}",
            error=f"failed to extract bindu source to {BINDU_SRC_DIR}",
        )

    async def _install_deps(
        self,
        client: Any,
        machine_id: str,
        has_pyproject: bool,
        has_requirements: bool,
        bindu_version: str | None = None,
    ) -> None:
        """Install bindu + the user's deps inside the VM (in ``APP_DIR``).

        ``--break-system-packages``: stock boxd images are Ubuntu 24.04
        where the system Python is "externally managed" (PEP 668) and
        plain ``pip install`` is refused. The VM is single-tenant.

        ``bindu_version`` cases:
          - ``"local"``: editable install from ``BINDU_SRC_DIR`` (must have
            been shipped via :meth:`_ship_bindu_source`).
          - ``"X.Y.Z"``: ``pip install bindu==X.Y.Z`` from PyPI.
          - ``None``: ``pip install bindu`` (latest from PyPI).
        """
        if bindu_version == "local":
            bindu_install = f"pip install --break-system-packages -e {BINDU_SRC_DIR}"
        elif bindu_version:
            bindu_install = (
                f"pip install --break-system-packages bindu=={bindu_version}"
            )
        else:
            bindu_install = "pip install --break-system-packages bindu"
        steps = [bindu_install]
        if has_requirements:
            steps.append(
                f"pip install --break-system-packages -r {APP_DIR}/requirements.txt"
            )
        if has_pyproject:
            steps.append(f"cd {APP_DIR} && pip install --break-system-packages -e .")
        # One round-trip with `&&` chaining so the first failure short-circuits.
        await _exec_or_raise(
            client,
            machine_id,
            "sh",
            "-c",
            " && ".join(steps),
            error="failed to install deps",
        )

    async def _start_agent(
        self,
        client: Any,
        machine_id: str,
        script: str,
        env: dict[str, str] | None = None,
        public_url: str | None = None,
    ) -> None:
        """Start the agent script inside the VM (detached via nohup).

        We invoke ``python3 <script>`` directly: published bindu wheels do
        not always ship the ``bindu`` console-script entry point, and the
        user's script calls ``bindufy()`` itself.

        On redeploy we kill the previously-started agent (tracked via a
        pidfile) before exec'ing the new one. Without this the old
        process keeps holding port 3773 and the new one's bind silently
        fails — ``/health`` keeps reporting OK from the old code.
        """
        merged_env = dict(env or {})
        if public_url:
            merged_env["BINDU_PUBLIC_URL"] = public_url

        # Step 1: graceful TERM + 5s wait + SIGKILL on the prior agent. Run
        # as its own exec so the next command sees a clean process table.
        # Combining this with the start command into one shell line confuses
        # ``&``/``&&`` precedence and ends up backgrounding the wrong subshell.
        kill_old = (
            f"if [ -f {AGENT_PID_PATH} ]; then "
            f"  OLD=$(cat {AGENT_PID_PATH}); "
            f"  kill $OLD 2>/dev/null || true; "
            f"  for _ in 1 2 3 4 5; do "
            f"    kill -0 $OLD 2>/dev/null || break; "
            f"    sleep 1; "
            f"  done; "
            f"  kill -9 $OLD 2>/dev/null || true; "
            f"  rm -f {AGENT_PID_PATH}; "
            f"fi"
        )
        await _exec_or_raise(
            client,
            machine_id,
            "sh",
            "-c",
            kill_old,
            error="failed to stop previous agent",
        )

        # Step 2: start the new agent detached. ``setsid`` puts it in its own
        # session so the gRPC exec channel closing doesn't cascade SIGHUP to
        # the python3 process. ``$!`` here is the python3 PID — the trailing
        # ``&`` only backgrounds that one command, not a wrapper subshell.
        start = (
            f"cd {APP_DIR} && "
            f"setsid nohup python3 {APP_DIR}/{script} "
            f"> {AGENT_LOG_PATH} 2>&1 < /dev/null & "
            f"echo $! > {AGENT_PID_PATH}"
        )
        await _exec_or_raise(
            client,
            machine_id,
            "sh",
            "-c",
            start,
            env=merged_env,
            error="failed to start agent",
        )

    async def _wait_healthy(self, url: str, timeout: float = _HEALTH_TIMEOUT) -> None:
        async with httpx.AsyncClient(timeout=5.0) as client:

            async def probe() -> bool:
                resp = await client.get(f"{url}/health")
                return resp.status_code == 200

            await _poll_until(
                probe,
                timeout=timeout,
                interval=_POLL_INTERVAL,
                error_msg=f"agent at {url} did not become healthy within {timeout}s",
            )

    @staticmethod
    def _detect_script_name(source_dir: Path) -> str:
        """Pick the agent's entry script.

        Prefers a top-level ``.py`` file that calls ``bindufy(``.
        """
        candidates = sorted(source_dir.glob("*.py"))
        for c in candidates:
            try:
                if "bindufy(" in c.read_text(errors="ignore"):
                    return c.name
            except OSError:
                continue
        if candidates:
            return candidates[0].name
        raise RuntimeError(
            f"no .py file found in {source_dir} to use as agent entry point"
        )

    async def deploy(
        self,
        agent_name: str,
        source_dir: Path | None,
        config: RuntimeConfig,
        env: dict[str, str] | None = None,
        script: str | None = None,
    ) -> RuntimeHandle:
        """Resolve the VM, ship source (A2) or use image (A1), start agent, wait healthy."""
        if not (os.environ.get("BOXD_API_KEY") or os.environ.get("BOXD_TOKEN")):
            raise RuntimeError(
                "BOXD_API_KEY or BOXD_TOKEN must be set in the host environment"
            )

        async with _make_client() as client:
            machine = await self._resolve_vm(client, agent_name, config)
            # Blocks until the machine is "running" AND exec round-trips —
            # covers fresh creates and the resume/wake path alike.
            machine = await client.machines.wait_until_ready(
                machine.id, timeout=_VM_READY_TIMEOUT
            )
            public_url = machine.access.url or f"https://{agent_name}.boxd.sh"

            # Point the machine's default proxy route at bindu's port on
            # every deploy (boxd's own default is a different port).
            # Idempotent.
            await client.machines.proxies.set_port(machine.id, BINDU_DEFAULT_PORT)

            if config.image is None:
                if source_dir is None:
                    raise RuntimeError(
                        "source_dir is required when config.image is not set"
                    )
                ship_tasks = [self._ship_source(client, machine.id, source_dir)]
                if config.bindu_version == "local":
                    ship_tasks.append(self._ship_bindu_source(client, machine.id))
                await asyncio.gather(*ship_tasks)
                has_pyproject = (source_dir / "pyproject.toml").exists()
                has_requirements = (source_dir / "requirements.txt").exists()
                await self._install_deps(
                    client,
                    machine.id,
                    has_pyproject=has_pyproject,
                    has_requirements=has_requirements,
                    bindu_version=config.bindu_version,
                )
                script_to_run = script or self._detect_script_name(source_dir)
                merged_env = {**config.env, **(env or {})}
                await self._start_agent(
                    client,
                    machine.id,
                    script=script_to_run,
                    env=merged_env,
                    public_url=public_url,
                )

            await self._wait_healthy(public_url, timeout=_HEALTH_TIMEOUT)

            return RuntimeHandle(
                name=agent_name,
                url=public_url,
                provider="boxd",
                metadata={"vm_id": machine.id},
            )

    async def health(self, handle: RuntimeHandle) -> bool:
        """Return True if the agent's ``/health`` endpoint returns 200."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{handle.url}/health")
                return resp.status_code == 200
        except httpx.HTTPError:
            return False

    async def stream_logs(
        self, handle: RuntimeHandle, follow: bool = True
    ) -> AsyncIterator[bytes]:
        """Yield chunks of the in-VM agent's stdout/stderr.

        ``machines.logs`` is the VM console — a detached nohup'd agent never
        writes there — so we tail ``AGENT_LOG_PATH`` over a streaming exec
        instead. ``tail -F`` is deliberate: it keeps polling when the file
        is missing or rotates, which matches the agent's startup window (the
        file appears as soon as the python3 process opens it for redirect).
        """
        async with _make_client() as client:
            machine = await _get_machine(client, handle.name)
            if machine is None:
                raise RuntimeError(f"no boxd machine named {handle.name}")
            command = (
                ["tail", "-n", "+1", "-F", AGENT_LOG_PATH]
                if follow
                else ["sh", "-c", f"cat {AGENT_LOG_PATH} 2>/dev/null || true"]
            )
            stream = client.machines.stream_exec(
                machine.id, command=command, close_stdin=True
            )
            async with stream:
                async for chunk in stream:
                    yield chunk

    async def on_exit(
        self,
        handle: RuntimeHandle,
        mode: Literal["suspend", "destroy", "detach"],
    ) -> None:
        """Apply the on-exit policy (``suspend`` / ``destroy`` / ``detach``).

        ``suspend`` actively calls ``machines.pause()`` (suspend to RAM)
        rather than waiting for the auto-suspend timer. The timer is disabled
        by default (so background tasks aren't frozen mid-flight while the
        agent is running), so relying on it would silently turn
        ``--on-exit=suspend`` into a no-op.
        """
        if mode == "detach":
            return
        async with _make_client() as client:
            try:
                machine = await _get_machine(client, handle.name)
            except Exception as e:
                logger.warning("on_exit could not look up VM %s: %s", handle.name, e)
                return
            if machine is None:
                logger.warning("on_exit: no boxd machine named %s", handle.name)
                return
            if mode == "destroy":
                await client.machines.delete(machine.id)
            elif mode == "suspend":
                try:
                    await client.machines.pause(machine.id)
                except Exception as e:
                    # The agent's still up; user can retry or destroy manually.
                    logger.warning("on_exit suspend failed for %s: %s", handle.name, e)


register_provider("boxd", BoxdRuntimeProvider)
