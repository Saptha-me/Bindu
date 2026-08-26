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


def _wire_safe_write_file(fake_box):
    """Make fake_box echo back the correct sha256 from sha256sum invocations.

    The real ``_safe_write_file`` writes a blob, then runs ``sha256sum`` on
    the destination and compares to the host's hash. To test the *callers*
    (ship_source, _ship_bindu_source, deploy()) we need the box to look like
    the bytes landed intact — so wire write_file to remember what was sent
    and exec to return the matching hash for sha256sum.
    """
    import hashlib

    last_blob: dict[str, bytes] = {}

    async def fake_write_file(blob, dest):
        last_blob[dest] = blob

    fake_box.write_file.side_effect = fake_write_file

    async def fake_exec(*args, **kwargs):
        if args and args[0] == "sha256sum" and len(args) >= 2:
            dest = args[1]
            blob = last_blob.get(dest, b"")
            r = MagicMock()
            r.exit_code = 0
            r.success = True
            r.stdout = f"{hashlib.sha256(blob).hexdigest()}  {dest}\n"
            r.stderr = ""
            return r
        return _ok_exec_result()

    fake_box.exec.side_effect = fake_exec


# ── _resolve_vm ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resolve_vm_creates_when_not_found(mock_boxd, fake_box):
    """If no VM with this name exists, create one."""
    from boxd.errors import NotFoundError

    mock_boxd.box.get.side_effect = NotFoundError("not found")
    p = BoxdRuntimeProvider()

    cfg = RuntimeConfig.from_dict({"provider": "boxd"})
    box = await p._resolve_vm(mock_boxd, "my-agent", cfg)

    mock_boxd.box.get.assert_awaited_once_with("my-agent")
    mock_boxd.box.create.assert_awaited_once()
    assert box is fake_box


@pytest.mark.asyncio
async def test_resolve_vm_reuses_when_found(mock_boxd, fake_box):
    """If a VM already exists, reuse it without creating."""
    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict({"provider": "boxd"})
    box = await p._resolve_vm(mock_boxd, "my-agent", cfg)

    mock_boxd.box.get.assert_awaited_once_with("my-agent")
    mock_boxd.box.create.assert_not_awaited()
    assert box is fake_box


@pytest.mark.asyncio
async def test_resolve_vm_passes_config(mock_boxd, fake_box):
    """vcpu / memory / disk / image / auto_suspend land in the create call."""
    from boxd.errors import NotFoundError

    mock_boxd.box.get.side_effect = NotFoundError("nope")
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

    call = mock_boxd.box.create.await_args
    assert call.kwargs.get("name") == "my-agent"
    assert call.kwargs.get("image") == "ghcr.io/me/agent:v1"
    box_config = call.kwargs.get("config")
    assert box_config is not None
    assert box_config.vcpu == 4
    assert box_config.memory == "8G"
    assert box_config.disk == "40G"
    # auto_suspend goes through LifecycleConfig
    assert box_config.lifecycle is not None
    assert box_config.lifecycle.auto_suspend_timeout == 30
    # default proxy must forward to bindu's default port (3773), not boxd's
    # default (8000), or the public URL is unreachable.
    assert box_config.network is not None
    assert box_config.network.proxies is not None
    assert any(p.port == 3773 for p in box_config.network.proxies)


# ── _ship_source ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ship_source_writes_and_extracts(mock_boxd, fake_box, tmp_path):
    (tmp_path / "agent.py").write_text("# hi\n")
    _wire_safe_write_file(fake_box)
    p = BoxdRuntimeProvider()

    await p._ship_source(fake_box, tmp_path)

    fake_box.write_file.assert_awaited_once()
    args = fake_box.write_file.await_args
    payload, dest = args.args[0], args.args[1]
    assert isinstance(payload, bytes)
    assert dest == "/tmp/source.tar.gz"

    # mkdir + tar extract are issued as a single shell exec to save a round-trip
    exec_calls = fake_box.exec.await_args_list
    assert any(
        c.args[0] == "sh"
        and c.args[1] == "-c"
        and "mkdir -p /home/boxd/app" in c.args[2]
        and "tar xzf /tmp/source.tar.gz -C /home/boxd/app" in c.args[2]
        for c in exec_calls
    )


# ── _safe_write_file (verify-and-retry workaround for boxd issue #45) ─


@pytest.mark.asyncio
async def test_safe_write_file_succeeds_on_clean_upload(fake_box):
    """When the sha256 on the VM matches the host, no retry."""
    from bindu.runtime.boxd_provider import _safe_write_file

    _wire_safe_write_file(fake_box)
    await _safe_write_file(fake_box, b"hello world", "/tmp/x.bin")

    assert fake_box.write_file.await_count == 1


@pytest.mark.asyncio
async def test_safe_write_file_retries_on_corrupted_upload(monkeypatch, fake_box):
    """If the first upload's hash mismatches, retry until it succeeds."""
    import hashlib

    from bindu.runtime.boxd_provider import _safe_write_file

    monkeypatch.setattr(
        "bindu.runtime.boxd_provider.asyncio.sleep", AsyncMock(return_value=None)
    )

    blob = b"some data"
    expected = hashlib.sha256(blob).hexdigest()
    state = {"call": 0}

    async def fake_write(b, d):
        pass

    async def fake_exec(*args, **kwargs):
        if args and args[0] == "sha256sum":
            state["call"] += 1
            r = MagicMock()
            r.exit_code = 0
            # First call returns a wrong hash (truncation simulated); second matches.
            hash_str = "0" * 64 if state["call"] == 1 else expected
            r.stdout = f"{hash_str}  {args[1]}\n"
            r.stderr = ""
            return r
        return _ok_exec_result()

    fake_box.write_file.side_effect = fake_write
    fake_box.exec.side_effect = fake_exec

    await _safe_write_file(fake_box, blob, "/tmp/x.bin")
    # Wrote twice (once corrupted, once clean)
    assert fake_box.write_file.await_count == 2


@pytest.mark.asyncio
async def test_safe_write_file_raises_after_max_retries(monkeypatch, fake_box):
    """If every attempt produces a corrupt upload, raise with a useful message."""
    from bindu.runtime.boxd_provider import _safe_write_file

    monkeypatch.setattr(
        "bindu.runtime.boxd_provider.asyncio.sleep", AsyncMock(return_value=None)
    )

    async def fake_write(b, d):
        pass

    async def fake_exec_always_wrong(*args, **kwargs):
        if args and args[0] == "sha256sum":
            r = MagicMock()
            r.exit_code = 0
            r.stdout = f"{'f' * 64}  {args[1]}\n"
            r.stderr = ""
            return r
        return _ok_exec_result()

    fake_box.write_file.side_effect = fake_write
    fake_box.exec.side_effect = fake_exec_always_wrong

    with pytest.raises(RuntimeError) as ei:
        await _safe_write_file(fake_box, b"data", "/tmp/x.bin")
    msg = str(ei.value)
    assert "corrupted" in msg
    assert "issues/45" in msg  # points at the upstream bug


# ── _install_deps ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_install_deps_with_pyproject(mock_boxd, fake_box):
    fake_box.exec.return_value = _ok_exec_result()
    p = BoxdRuntimeProvider()

    await p._install_deps(fake_box, has_pyproject=True, has_requirements=False)

    # All pip steps are chained into a single sh -c invocation to save round-trips.
    install_calls = [
        c
        for c in fake_box.exec.await_args_list
        if c.args and c.args[0] == "sh" and "pip install" in c.args[2]
    ]
    assert len(install_calls) == 1
    cmd = install_calls[0].args[2]
    assert "pip install --break-system-packages bindu" in cmd
    assert "pip install --break-system-packages -e ." in cmd


@pytest.mark.asyncio
async def test_install_deps_with_requirements(mock_boxd, fake_box):
    fake_box.exec.return_value = _ok_exec_result()
    p = BoxdRuntimeProvider()

    await p._install_deps(fake_box, has_pyproject=False, has_requirements=True)

    install_calls = [
        c
        for c in fake_box.exec.await_args_list
        if c.args and c.args[0] == "sh" and "pip install" in c.args[2]
    ]
    assert len(install_calls) == 1
    cmd = install_calls[0].args[2]
    assert (
        "pip install --break-system-packages -r /home/boxd/app/requirements.txt" in cmd
    )


@pytest.mark.asyncio
async def test_install_deps_pinned_bindu_version(mock_boxd, fake_box):
    fake_box.exec.return_value = _ok_exec_result()
    p = BoxdRuntimeProvider()

    await p._install_deps(
        fake_box,
        has_pyproject=False,
        has_requirements=False,
        bindu_version="0.2.5",
    )

    install_calls = [
        c
        for c in fake_box.exec.await_args_list
        if c.args and c.args[0] == "sh" and "pip install" in c.args[2]
    ]
    assert len(install_calls) == 1
    assert (
        "pip install --break-system-packages bindu==0.2.5" in install_calls[0].args[2]
    )


@pytest.mark.asyncio
async def test_install_deps_raises_on_failure(mock_boxd, fake_box):
    """Non-zero exit code from pip install should raise."""
    bad = MagicMock()
    bad.exit_code = 1
    bad.stderr = "boom"
    fake_box.exec.return_value = bad
    p = BoxdRuntimeProvider()

    with pytest.raises(RuntimeError, match="failed"):
        await p._install_deps(fake_box, has_pyproject=False, has_requirements=False)


@pytest.mark.asyncio
async def test_install_deps_bindu_version_local(mock_boxd, fake_box):
    """bindu_version='local' installs bindu editable from BINDU_SRC_DIR."""
    from bindu.runtime.boxd_provider import BINDU_SRC_DIR

    fake_box.exec.return_value = _ok_exec_result()
    p = BoxdRuntimeProvider()

    await p._install_deps(
        fake_box,
        has_pyproject=False,
        has_requirements=False,
        bindu_version="local",
    )
    install_calls = [
        c
        for c in fake_box.exec.await_args_list
        if c.args and c.args[0] == "sh" and "pip install" in c.args[2]
    ]
    assert len(install_calls) == 1
    cmd = install_calls[0].args[2]
    assert f"pip install --break-system-packages -e {BINDU_SRC_DIR}" in cmd
    # Must NOT pull from PyPI when local mode is requested.
    assert "bindu==" not in cmd
    assert "pip install --break-system-packages bindu " not in cmd


# ── _start_agent ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_agent_execs_bindu_serve(mock_boxd, fake_box):
    p = BoxdRuntimeProvider()
    fake_box.exec.return_value = _ok_exec_result()

    await p._start_agent(
        fake_box,
        script="my_agent.py",
        env={"FOO": "bar"},
        public_url="https://my-agent.boxd.sh",
    )

    fake_box.exec.assert_awaited()
    cmd_call = fake_box.exec.await_args
    assert cmd_call.args[0] == "sh"
    assert cmd_call.args[1] == "-c"
    cmd_str = cmd_call.args[2]
    assert "python3" in cmd_str
    assert "/home/boxd/app/my_agent.py" in cmd_str
    # env from caller plus the auto-injected BINDU_PUBLIC_URL
    env = cmd_call.kwargs.get("env")
    assert env is not None
    assert env.get("FOO") == "bar"
    assert env.get("BINDU_PUBLIC_URL") == "https://my-agent.boxd.sh"


@pytest.mark.asyncio
async def test_start_agent_kills_old_pid_and_writes_new(mock_boxd, fake_box):
    """Redeploy must SIGTERM the previous python3 (tracked via pidfile),
    wait for it to die, then start the new one and record its PID.

    Implementation note: kill-old and start run as two separate execs.
    Combining them into one shell line confuses ``&`` precedence and
    backgrounds the wrong subshell — easy to miss without splitting.
    """
    p = BoxdRuntimeProvider()
    fake_box.exec.return_value = _ok_exec_result()

    await p._start_agent(fake_box, script="agent.py")
    sh_calls = [c.args[2] for c in fake_box.exec.await_args_list if c.args[0] == "sh"]
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
async def test_start_agent_raises_on_nonzero_exit(mock_boxd, fake_box):
    bad = MagicMock()
    bad.exit_code = 1
    bad.stderr = "boom"
    fake_box.exec.return_value = bad

    p = BoxdRuntimeProvider()
    # First exec (kill-old) raises with this message; we accept either
    # since both phases are "starting" from the user's POV.
    with pytest.raises(RuntimeError, match="(failed to start|failed to stop)"):
        await p._start_agent(fake_box, script="agent.py")


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
    mock_boxd, fake_box, tmp_path, fake_health, boxd_api_key
):
    """A2 deploy: source ship + install + start + healthy."""
    (tmp_path / "agent.py").write_text(
        "from bindu.penguin.bindufy import bindufy\nbindufy({}, lambda m: 'hi')\n"
    )
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\nversion='0.1.0'\n")
    _wire_safe_write_file(fake_box)
    fake_box.name = "my-agent"
    fake_box.url = "https://my-agent.boxd.sh"

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

    fake_box.write_file.assert_awaited_once()
    pip_calls = [
        c
        for c in fake_box.exec.await_args_list
        if c.args and c.args[0] == "sh" and "pip install" in c.args[2]
    ]
    assert pip_calls, "pip install should have been called"
    serve_calls = [
        c
        for c in fake_box.exec.await_args_list
        if c.args and c.args[0] == "sh" and "python3" in c.args[2]
    ]
    assert serve_calls, "agent script should have been started"


@pytest.mark.asyncio
async def test_deploy_a1_skips_source(mock_boxd, fake_box, fake_health, boxd_api_key):
    """A1 deploy: image-based; no source ship, no pip install."""
    from boxd.errors import NotFoundError

    mock_boxd.box.get.side_effect = NotFoundError("nope")
    fake_box.exec.return_value = _ok_exec_result()
    fake_box.name = "my-agent"
    fake_box.url = "https://my-agent.boxd.sh"

    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict({"provider": "boxd", "image": "ghcr.io/me/agent:v1"})

    handle = await p.deploy(
        agent_name="my-agent",
        source_dir=None,
        config=cfg,
        env=None,
    )

    assert handle.url == "https://my-agent.boxd.sh"
    fake_box.write_file.assert_not_awaited()
    pip_calls = [
        c
        for c in fake_box.exec.await_args_list
        if c.args and c.args[0] == "sh" and "pip install" in c.args[2]
    ]
    assert not pip_calls


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
    mock_boxd, fake_box, tmp_path, fake_health, boxd_api_key
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
    _wire_safe_write_file(fake_box)
    fake_box.name = "agent"
    fake_box.url = "https://agent.boxd.sh"

    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict({"provider": "boxd"})

    await p.deploy(
        agent_name="agent",
        source_dir=tmp_path,
        config=cfg,
        env=None,
        script="real_agent.py",
    )

    serve_calls = [
        c
        for c in fake_box.exec.await_args_list
        if c.args and c.args[0] == "sh" and "python3" in c.args[2]
    ]
    assert serve_calls, "agent script should have been started"
    cmd_str = serve_calls[0].args[2]
    assert "real_agent.py" in cmd_str
    # Detection fallback would have picked stale_agent.py (sorts first).
    assert "stale_agent.py" not in cmd_str


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
async def test_on_exit_destroy(mock_boxd, fake_box, boxd_api_key):
    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {"vm_id": "vm-1"})
    await p.on_exit(h, "destroy")
    fake_box.destroy.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_exit_suspend_actively_suspends(mock_boxd, fake_box, boxd_api_key):
    """suspend mode calls box.suspend() — not a no-op.

    The auto-suspend timer is disabled by default (so background tasks
    aren't frozen mid-flight while the agent is running), so relying on the
    timer would silently turn ``--on-exit=suspend`` into ``--on-exit=detach``.
    """
    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {})
    await p.on_exit(h, "suspend")
    fake_box.suspend.assert_awaited_once()
    fake_box.destroy.assert_not_awaited()


@pytest.mark.asyncio
async def test_on_exit_suspend_swallows_errors(mock_boxd, fake_box, boxd_api_key):
    """If box.suspend() raises, on_exit returns cleanly — host shutdown
    shouldn't bubble VM-side errors to the user's terminal."""
    fake_box.suspend.side_effect = RuntimeError("boxd had a moment")
    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {})
    # Must not raise.
    await p.on_exit(h, "suspend")
    fake_box.suspend.assert_awaited_once()


@pytest.mark.asyncio
async def test_on_exit_detach_is_pure_noop(mock_boxd, fake_box, boxd_api_key):
    """detach mode does not even open a connection."""
    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {})
    await p.on_exit(h, "detach")
    fake_box.destroy.assert_not_awaited()
    fake_box.suspend.assert_not_awaited()
    mock_boxd.box.get.assert_not_awaited()


def _exec_proc_with_chunks(chunks):
    """Build a fake ``ExecProcess`` whose .stdout yields the given chunks."""

    class _Stdout:
        def __init__(self, cs):
            self._cs = list(cs)

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self._cs:
                raise StopAsyncIteration
            return self._cs.pop(0)

    proc = MagicMock()
    proc.stdout = _Stdout(chunks)
    return proc


@pytest.mark.asyncio
async def test_stream_logs_tails_agent_log(mock_boxd, fake_box, boxd_api_key):
    """stream_logs(follow=True) issues ``tail -F AGENT_LOG_PATH`` over a
    streaming exec, and passes the chunks through unchanged."""
    from bindu.runtime.boxd_provider import AGENT_LOG_PATH

    chunks = [b"agent up\n", b"served /\n"]
    fake_box.exec = AsyncMock(return_value=_exec_proc_with_chunks(chunks))
    mock_boxd.box.get.return_value = fake_box

    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {})
    out = []
    async for chunk in p.stream_logs(h, follow=True):
        out.append(chunk)

    assert out == chunks
    call = fake_box.exec.await_args
    assert call is not None, "await_args should not be None"
    assert call.args[0] == "tail"
    assert "-F" in call.args
    assert AGENT_LOG_PATH in call.args
    assert call.kwargs.get("stream") is True


@pytest.mark.asyncio
async def test_stream_logs_no_follow_uses_cat(mock_boxd, fake_box, boxd_api_key):
    """stream_logs(follow=False) prints current contents and ends.

    Implementation uses ``sh -c "cat ... 2>/dev/null || true"`` so a missing
    log file doesn't surface a confusing exec error.
    """
    fake_box.exec = AsyncMock(return_value=_exec_proc_with_chunks([b"static\n"]))
    mock_boxd.box.get.return_value = fake_box

    p = BoxdRuntimeProvider()
    h = RuntimeHandle("my-agent", "https://my-agent.boxd.sh", "boxd", {})
    out = [chunk async for chunk in p.stream_logs(h, follow=False)]
    assert out == [b"static\n"]
    call = fake_box.exec.await_args
    assert call is not None, "await_args should not be None"
    # Either tail-without-F or cat with a no-error wrapper is fine; check that
    # the streamed command does NOT contain ``-F`` (which would tail forever).
    assert "-F" not in call.args
    assert call.kwargs.get("stream") is True
