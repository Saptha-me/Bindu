"""Tests for BoxdRuntimeProvider — all with the boxd SDK mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from bindu.runtime import RuntimeConfig
from bindu.runtime.base import RuntimeHandle
from bindu.runtime.boxd_provider import BoxdRuntimeProvider


def _ok_exec_result():
    """Stub ExecResult with exit_code=0."""
    r = MagicMock()
    r.exit_code = 0
    r.success = True
    r.stdout = ""
    r.stderr = ""
    return r


def _bad_exec_result(stderr: str = "boom"):
    r = MagicMock()
    r.exit_code = 1
    r.success = False
    r.stdout = ""
    r.stderr = stderr
    return r


def _sh_calls(fake_client):
    """Extract the shell script strings from ``sh -c`` exec invocations.

    The provider calls ``machines.exec(machine_id, ["sh", "-c", script])``.
    """
    out = []
    for c in fake_client.machines.exec.await_args_list:
        cmd = c.args[1]
        if isinstance(cmd, list) and cmd[:2] == ["sh", "-c"]:
            out.append(cmd[2])
    return out


# ── _resolve_vm ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_vm_creates_when_not_found(mock_boxd, fake_machine):
    """If no machine with this name exists, create one."""
    from boxd import NotFoundError

    mock_boxd.machines.get.side_effect = NotFoundError("not found")
    p = BoxdRuntimeProvider()

    cfg = RuntimeConfig.from_dict({"provider": "boxd"})
    machine = await p._resolve_vm(mock_boxd, "my-agent", cfg)

    mock_boxd.machines.get.assert_awaited_once_with("my-agent")
    mock_boxd.machines.create.assert_awaited_once()
    assert machine is fake_machine


@pytest.mark.asyncio
async def test_resolve_vm_reuses_when_found(mock_boxd, fake_machine):
    """If a machine already exists and is running, reuse it as-is."""
    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict({"provider": "boxd"})
    machine = await p._resolve_vm(mock_boxd, "my-agent", cfg)

    mock_boxd.machines.get.assert_awaited_once_with("my-agent")
    mock_boxd.machines.create.assert_not_awaited()
    mock_boxd.machines.resume.assert_not_awaited()
    assert machine is fake_machine


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "verb"),
    [("suspended", "resume"), ("hibernated", "wake"), ("stopped", "start")],
)
async def test_resolve_vm_revives_saved_machine(mock_boxd, fake_machine, status, verb):
    """A reused machine left paused/hibernated/stopped by a previous
    ``on_exit`` must be brought back explicitly — boxd 0.2.x never resumes
    implicitly, and ``wait_until_ready`` raises on 'stopped'."""
    fake_machine.status = status
    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict({"provider": "boxd"})

    await p._resolve_vm(mock_boxd, "my-agent", cfg)

    getattr(mock_boxd.machines, verb).assert_awaited_once_with(fake_machine.id)
    mock_boxd.machines.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_vm_falls_back_to_list_on_name_miss(mock_boxd, fake_machine):
    """``machines.get(name)`` resolves names only in the default org
    context; a machine living in another org raises NotFound while
    ``list()`` still shows it. The provider must find it via the list scan
    and reuse it — creating over the name fails with ConflictError."""
    from boxd import NotFoundError

    mock_boxd.machines.get.side_effect = NotFoundError("not found")
    fake_machine.name = "my-agent"
    mock_boxd.machines.list.return_value = [fake_machine]
    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict({"provider": "boxd"})

    machine = await p._resolve_vm(mock_boxd, "my-agent", cfg)

    assert machine is fake_machine
    mock_boxd.machines.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_resolve_vm_passes_config(mock_boxd, fake_machine):
    """vcpu / memory / disk / image / auto_suspend land in the create call."""
    from boxd import NotFoundError

    mock_boxd.machines.get.side_effect = NotFoundError("nope")
    p = BoxdRuntimeProvider()

    cfg = RuntimeConfig.from_dict(
        {
            "provider": "boxd",
            "image": "ghcr.io/me/agent:v1",
            "vcpu": 4,
            "memory": "8G",
            "disk": "40G",
            "auto_suspend": 30,
        }
    )
    await p._resolve_vm(mock_boxd, "my-agent", cfg)

    call = mock_boxd.machines.create.await_args
    assert call.args[0] == "my-agent"
    assert call.kwargs.get("image") == "ghcr.io/me/agent:v1"
    assert call.kwargs.get("vcpu") == 4
    assert call.kwargs.get("memory") == "8G"
    assert call.kwargs.get("disk") == "40G"
    assert call.kwargs.get("auto_suspend_timeout") == 30


# ── _ship_source ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ship_source_uploads_and_extracts(mock_boxd, fake_machine, tmp_path):
    (tmp_path / "agent.py").write_text("# hi\n")
    p = BoxdRuntimeProvider()

    await p._ship_source(mock_boxd, fake_machine.id, tmp_path)

    mock_boxd.machines.files.upload.assert_awaited_once()
    args = mock_boxd.machines.files.upload.await_args
    machine_id, dest, payload = args.args[0], args.args[1], args.args[2]
    assert machine_id == fake_machine.id
    assert dest == "/tmp/source.tar.gz"
    assert isinstance(payload, bytes)

    # mkdir + tar extract are issued as a single shell exec to save a round-trip
    assert any(
        "mkdir -p /home/boxd/app" in s
        and "tar xzf /tmp/source.tar.gz -C /home/boxd/app" in s
        for s in _sh_calls(mock_boxd)
    )


# ── _upload_file (verify the confirmed byte count) ─────────────────


@pytest.mark.asyncio
async def test_upload_file_accepts_confirmed_full_write(mock_boxd, fake_machine):
    """When the machine confirms all bytes, no error."""
    from bindu.runtime.boxd_provider import _upload_file

    await _upload_file(mock_boxd, fake_machine.id, b"hello world", "/tmp/x.bin")

    mock_boxd.machines.files.upload.assert_awaited_once_with(
        fake_machine.id, "/tmp/x.bin", b"hello world"
    )


@pytest.mark.asyncio
async def test_upload_file_raises_on_short_write(mock_boxd, fake_machine):
    """If the machine confirms fewer bytes than sent, fail the deploy."""
    from bindu.runtime.boxd_provider import _upload_file

    mock_boxd.machines.files.upload.side_effect = None
    mock_boxd.machines.files.upload.return_value = 3

    with pytest.raises(RuntimeError, match="incomplete"):
        await _upload_file(mock_boxd, fake_machine.id, b"some data", "/tmp/x.bin")


# ── _install_deps ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_install_deps_with_pyproject(mock_boxd, fake_machine):
    p = BoxdRuntimeProvider()

    await p._install_deps(
        mock_boxd, fake_machine.id, has_pyproject=True, has_requirements=False
    )

    # All pip steps are chained into a single sh -c invocation to save round-trips.
    install_calls = [s for s in _sh_calls(mock_boxd) if "pip install" in s]
    assert len(install_calls) == 1
    cmd = install_calls[0]
    assert "pip install --break-system-packages bindu" in cmd
    assert "pip install --break-system-packages -e ." in cmd


@pytest.mark.asyncio
async def test_install_deps_with_requirements(mock_boxd, fake_machine):
    p = BoxdRuntimeProvider()

    await p._install_deps(
        mock_boxd, fake_machine.id, has_pyproject=False, has_requirements=True
    )

    install_calls = [s for s in _sh_calls(mock_boxd) if "pip install" in s]
    assert len(install_calls) == 1
    assert (
        "pip install --break-system-packages -r /home/boxd/app/requirements.txt"
        in install_calls[0]
    )


@pytest.mark.asyncio
async def test_install_deps_pinned_bindu_version(mock_boxd, fake_machine):
    p = BoxdRuntimeProvider()

    await p._install_deps(
        mock_boxd,
        fake_machine.id,
        has_pyproject=False,
        has_requirements=False,
        bindu_version="0.2.5",
    )

    install_calls = [s for s in _sh_calls(mock_boxd) if "pip install" in s]
    assert len(install_calls) == 1
    assert "pip install --break-system-packages bindu==0.2.5" in install_calls[0]


@pytest.mark.asyncio
async def test_install_deps_raises_on_failure(mock_boxd, fake_machine):
    """Non-zero exit code from pip install should raise."""
    mock_boxd.machines.exec.return_value = _bad_exec_result()
    p = BoxdRuntimeProvider()

    with pytest.raises(RuntimeError, match="failed"):
        await p._install_deps(
            mock_boxd, fake_machine.id, has_pyproject=False, has_requirements=False
        )


@pytest.mark.asyncio
async def test_install_deps_bindu_version_local(mock_boxd, fake_machine):
    """bindu_version='local' installs bindu editable from BINDU_SRC_DIR."""
    from bindu.runtime.boxd_provider import BINDU_SRC_DIR

    p = BoxdRuntimeProvider()

    await p._install_deps(
        mock_boxd,
        fake_machine.id,
        has_pyproject=False,
        has_requirements=False,
        bindu_version="local",
    )
    install_calls = [s for s in _sh_calls(mock_boxd) if "pip install" in s]
    assert len(install_calls) == 1
    cmd = install_calls[0]
    assert f"pip install --break-system-packages -e {BINDU_SRC_DIR}" in cmd
    # Must NOT pull from PyPI when local mode is requested.
    assert "bindu==" not in cmd
    assert "pip install --break-system-packages bindu " not in cmd


# ── _start_agent ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_agent_execs_bindu_serve(mock_boxd, fake_machine):
    p = BoxdRuntimeProvider()

    await p._start_agent(
        mock_boxd,
        fake_machine.id,
        script="my_agent.py",
        env={"FOO": "bar"},
        public_url="https://my-agent.boxd.sh",
    )

    cmd_call = mock_boxd.machines.exec.await_args
    cmd = cmd_call.args[1]
    assert cmd[:2] == ["sh", "-c"]
    assert "python3" in cmd[2]
    assert "/home/boxd/app/my_agent.py" in cmd[2]
    # env from caller plus the auto-injected BINDU_PUBLIC_URL
    env = cmd_call.kwargs.get("env")
    assert env is not None
    assert env.get("FOO") == "bar"
    assert env.get("BINDU_PUBLIC_URL") == "https://my-agent.boxd.sh"


@pytest.mark.asyncio
async def test_start_agent_kills_old_pid_and_writes_new(mock_boxd, fake_machine):
    """Redeploy must SIGTERM the previous python3 (tracked via pidfile),
    wait for it to die, then start the new one and record its PID.

    Implementation note: kill-old and start run as two separate execs.
    Combining them into one shell line confuses ``&`` precedence and
    backgrounds the wrong subshell — easy to miss without splitting.
    """
    p = BoxdRuntimeProvider()

    await p._start_agent(mock_boxd, fake_machine.id, script="agent.py")
    sh_calls = _sh_calls(mock_boxd)
    assert len(sh_calls) == 2, "expected two execs: kill-old then start"
    kill_cmd, start_cmd = sh_calls
    # First exec: pidfile check + TERM + poll + SIGKILL fallback.
    assert "/tmp/bindu-agent.pid" in kill_cmd
    assert "kill $OLD" in kill_cmd
    assert "kill -9 $OLD" in kill_cmd
    # Second exec: start detached, record new PID.
    assert "setsid" in start_cmd
    assert "python3" in start_cmd
    assert "echo $! > /tmp/bindu-agent.pid" in start_cmd


@pytest.mark.asyncio
async def test_start_agent_raises_on_nonzero_exit(mock_boxd, fake_machine):
    mock_boxd.machines.exec.return_value = _bad_exec_result()

    p = BoxdRuntimeProvider()
    # First exec (kill-old) raises with this message; we accept either
    # since both phases are "starting" from the user's POV.
    with pytest.raises(RuntimeError, match="(failed to start|failed to stop)"):
        await p._start_agent(mock_boxd, fake_machine.id, script="agent.py")


# ── _wait_healthy ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_wait_healthy_returns_when_200(monkeypatch):
    """Health check returns once /health responds 200."""
    p = BoxdRuntimeProvider()

    call_count = {"n": 0}

    class _Resp:
        def __init__(self, status: int):
            self.status_code = status

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url):
            call_count["n"] += 1
            if call_count["n"] < 3:
                return _Resp(503)
            return _Resp(200)

    monkeypatch.setattr(
        "bindu.runtime.boxd_provider.httpx.AsyncClient",
        lambda *a, **kw: _FakeClient(),
    )
    # Avoid the 1s sleep inside the loop in tests
    monkeypatch.setattr(
        "bindu.runtime.boxd_provider.asyncio.sleep",
        AsyncMock(return_value=None),
    )

    await p._wait_healthy("https://my-agent.boxd.sh", timeout=10.0)
    assert call_count["n"] == 3


@pytest.mark.asyncio
async def test_wait_healthy_times_out(monkeypatch):
    p = BoxdRuntimeProvider()

    class _Resp:
        status_code = 503

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url):
            return _Resp()

    monkeypatch.setattr(
        "bindu.runtime.boxd_provider.httpx.AsyncClient",
        lambda *a, **kw: _FakeClient(),
    )
    monkeypatch.setattr(
        "bindu.runtime.boxd_provider.asyncio.sleep",
        AsyncMock(return_value=None),
    )

    with pytest.raises(TimeoutError, match="health"):
        await p._wait_healthy("https://my-agent.boxd.sh", timeout=0.1)


# ── deploy() integration ───────────────────────────────────────────


@pytest.fixture
def fake_health(monkeypatch):
    """Skip the actual health-check loop in deploy() tests."""

    async def fake(self, url, timeout=60.0):
        return None

    monkeypatch.setattr(BoxdRuntimeProvider, "_wait_healthy", fake)


@pytest.fixture
def boxd_api_key(monkeypatch):
    monkeypatch.setenv("BOXD_API_KEY", "bxk_test")


@pytest.mark.asyncio
async def test_deploy_a2_full_flow(
    mock_boxd, fake_machine, tmp_path, fake_health, boxd_api_key
):
    """A2 deploy: source ship + install + start + healthy."""
    (tmp_path / "agent.py").write_text(
        "from bindu.penguin.bindufy import bindufy\nbindufy({}, lambda m: 'hi')\n"
    )
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.1.0'\n")
    fake_machine.name = "my-agent"
    fake_machine.access.url = "https://my-agent.boxd.sh"

    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict({"provider": "boxd"})

    handle = await p.deploy(
        agent_name="my-agent",
        source_dir=tmp_path,
        config=cfg,
        env={"OPENAI_API_KEY": "sk-test"},  # pragma: allowlist secret
    )

    assert handle.name == "my-agent"
    assert handle.url == "https://my-agent.boxd.sh"
    assert handle.provider == "boxd"
    assert handle.metadata.get("vm_id") == "vm-1"

    mock_boxd.machines.wait_until_ready.assert_awaited_once()
    mock_boxd.machines.files.upload.assert_awaited_once()
    # The default proxy route must forward to bindu's port (3773), not
    # boxd's default, or the public URL is unreachable.
    mock_boxd.machines.proxies.set_port.assert_awaited_once_with(fake_machine.id, 3773)
    sh_calls = _sh_calls(mock_boxd)
    assert any("pip install" in s for s in sh_calls), "pip install expected"
    assert any("python3" in s for s in sh_calls), "agent start expected"


@pytest.mark.asyncio
async def test_deploy_a1_skips_source(
    mock_boxd, fake_machine, fake_health, boxd_api_key
):
    """A1 deploy: image-based; no source ship, no pip install."""
    from boxd import NotFoundError

    mock_boxd.machines.get.side_effect = NotFoundError("nope")
    fake_machine.name = "my-agent"
    fake_machine.access.url = "https://my-agent.boxd.sh"

    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict({"provider": "boxd", "image": "ghcr.io/me/agent:v1"})

    handle = await p.deploy(
        agent_name="my-agent",
        source_dir=None,
        config=cfg,
        env=None,
    )

    assert handle.url == "https://my-agent.boxd.sh"
    mock_boxd.machines.files.upload.assert_not_awaited()
    assert not [s for s in _sh_calls(mock_boxd) if "pip install" in s]


@pytest.mark.asyncio
async def test_deploy_requires_credentials(monkeypatch):
    """Missing BOXD_API_KEY/BOXD_TOKEN → raise actionable error."""
    monkeypatch.delenv("BOXD_API_KEY", raising=False)
    monkeypatch.delenv("BOXD_TOKEN", raising=False)
    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict({"provider": "boxd"})

    with pytest.raises(RuntimeError, match="BOXD_API_KEY"):
        await p.deploy("agent", None, cfg, None)


@pytest.mark.asyncio
async def test_deploy_uses_explicit_script_over_detection(
    mock_boxd, fake_machine, tmp_path, fake_health, boxd_api_key
):
    """When ``script=`` is passed, the VM runs that exact path — even if
    multiple .py files at the source root call bindufy()."""
    # Two scripts, both call bindufy(). _detect_script_name would pick
    # whichever sorts first; the explicit ``script=`` arg must win.
    (tmp_path / "real_agent.py").write_text(
        "from bindu.penguin.bindufy import bindufy\nbindufy({}, lambda m: 'hi')\n"
    )
    (tmp_path / "stale_agent.py").write_text(
        "from bindu.penguin.bindufy import bindufy\nbindufy({}, lambda m: 'old')\n"
    )
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.1.0'\n")

    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict({"provider": "boxd"})

    await p.deploy(
        agent_name="agent",
        source_dir=tmp_path,
        config=cfg,
        env=None,
        script="real_agent.py",
    )

    serve_calls = [s for s in _sh_calls(mock_boxd) if "python3" in s]
    assert serve_calls, "agent script should have been started"
    assert "real_agent.py" in serve_calls[0]
    # Detection fallback would have picked stale_agent.py (sorts first).
    assert "stale_agent.py" not in serve_calls[0]


# ── health / stream_logs / on_exit ────────────────────────────────


@pytest.mark.asyncio
async def test_health_returns_true_when_200(monkeypatch):
    p = BoxdRuntimeProvider()

    class _Resp:
        status_code = 200

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url):
            return _Resp()

    monkeypatch.setattr(
        "bindu.runtime.boxd_provider.httpx.AsyncClient",
        lambda *a, **kw: _FakeClient(),
    )
    h = RuntimeHandle("a", "https://a.boxd.sh", "boxd", {})
    assert await p.health(h) is True


@pytest.mark.asyncio
async def test_health_returns_false_when_unreachable(monkeypatch):
    p = BoxdRuntimeProvider()

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url):
            raise httpx.ConnectError("boom")

    monkeypatch.setattr(
        "bindu.runtime.boxd_provider.httpx.AsyncClient",
        lambda *a, **kw: _FakeClient(),
    )
    h = RuntimeHandle("a", "https://a.boxd.sh", "boxd", {})
    assert await p.health(h) is False


@pytest.mark.asyncio
async def test_on_exit_destroy(mock_boxd, fake_machine, boxd_api_key):
    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {"vm_id": "vm-1"})
    await p.on_exit(h, "destroy")
    mock_boxd.machines.delete.assert_awaited_once_with(fake_machine.id)


@pytest.mark.asyncio
async def test_on_exit_suspend_actively_pauses(mock_boxd, fake_machine, boxd_api_key):
    """suspend mode calls machines.pause() — not a no-op.

    The auto-suspend timer is disabled by default (so background tasks
    aren't frozen mid-flight while the agent is running), so relying on the
    timer would silently turn ``--on-exit=suspend`` into ``--on-exit=detach``.
    """
    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {})
    await p.on_exit(h, "suspend")
    mock_boxd.machines.pause.assert_awaited_once_with(fake_machine.id)
    mock_boxd.machines.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_exit_suspend_swallows_errors(mock_boxd, fake_machine, boxd_api_key):
    """If machines.pause() raises, on_exit returns cleanly — host shutdown
    shouldn't bubble VM-side errors to the user's terminal."""
    mock_boxd.machines.pause.side_effect = RuntimeError("boxd had a moment")
    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {})
    # Must not raise.
    await p.on_exit(h, "suspend")
    mock_boxd.machines.pause.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_exit_detach_is_pure_noop(mock_boxd, fake_machine, boxd_api_key):
    """detach mode does not even open a connection."""
    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {})
    await p.on_exit(h, "detach")
    mock_boxd.machines.delete.assert_not_awaited()
    mock_boxd.machines.pause.assert_not_awaited()
    mock_boxd.machines.get.assert_not_awaited()


class _FakeStream:
    """Stand-in for boxd's AsyncExecStream (async CM + async iterator)."""

    def __init__(self, chunks):
        self._cs = list(chunks)
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        self.closed = True

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._cs:
            raise StopAsyncIteration
        return self._cs.pop(0)


@pytest.mark.asyncio
async def test_stream_logs_tails_agent_log(mock_boxd, fake_machine, boxd_api_key):
    """stream_logs(follow=True) issues ``tail -F AGENT_LOG_PATH`` over a
    streaming exec, and passes the chunks through unchanged."""
    from bindu.runtime.boxd_provider import AGENT_LOG_PATH

    chunks = [b"agent up\n", b"served /\n"]
    fake_stream = _FakeStream(chunks)
    mock_boxd.machines.stream_exec.return_value = fake_stream

    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {})
    out = []
    async for chunk in p.stream_logs(h, follow=True):
        out.append(chunk)

    assert out == chunks
    assert fake_stream.closed
    call = mock_boxd.machines.stream_exec.call_args
    assert call.args[0] == fake_machine.id
    command = call.kwargs.get("command")
    assert command[0] == "tail"
    assert "-F" in command
    assert AGENT_LOG_PATH in command


@pytest.mark.asyncio
async def test_stream_logs_no_follow_uses_cat(mock_boxd, fake_machine, boxd_api_key):
    """stream_logs(follow=False) prints current contents and ends.

    Implementation uses ``sh -c "cat ... 2>/dev/null || true"`` so a missing
    log file doesn't surface a confusing exec error.
    """
    mock_boxd.machines.stream_exec.return_value = _FakeStream([b"static\n"])

    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {})
    out = [chunk async for chunk in p.stream_logs(h, follow=False)]
    assert out == [b"static\n"]
    command = mock_boxd.machines.stream_exec.call_args.kwargs.get("command")
    # Must NOT contain ``-F`` (which would tail forever).
    assert "-F" not in command
