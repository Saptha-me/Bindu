"""Fixtures for runtime provider unit tests."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest


def _ok_exec_result():
    """Stub ExecResult with exit_code=0."""
    r = MagicMock()
    r.exit_code = 0
    r.success = True
    r.stdout = ""
    r.stderr = ""
    return r


class _FakeMachine:
    """Stand-in for the boxd 0.2.x ``Machine`` record (plain data)."""

    def __init__(self, name: str = "agent", vm_id: str = "vm-1"):
        self.id = vm_id
        self.name = name
        self.status = "running"
        self.image_ref = "ubuntu:latest"
        self.boot_time_ms = 2000
        self.access = SimpleNamespace(
            url=f"https://{name}.boxd.sh",
            domain=f"{name}.boxd.sh",
            ssh_port=None,
        )


class _FakeMachines:
    """Stand-in for ``AsyncBoxd().machines`` (verbs + sub-namespaces)."""

    def __init__(self):
        self.create = AsyncMock()
        self.get = AsyncMock()
        self.list = AsyncMock(return_value=[])
        self.delete = AsyncMock()
        self.pause = AsyncMock()
        self.resume = AsyncMock()
        self.wake = AsyncMock()
        self.start = AsyncMock()
        self.wait_until_ready = AsyncMock()
        self.exec = AsyncMock(return_value=_ok_exec_result())
        # ``stream_exec`` is sync — it returns the stream session directly.
        self.stream_exec = MagicMock()
        self.logs = MagicMock()
        self.files = SimpleNamespace(upload=AsyncMock(), download=AsyncMock())
        self.proxies = SimpleNamespace(
            create=AsyncMock(),
            list=AsyncMock(return_value=[]),
            set_port=AsyncMock(),
            delete=AsyncMock(),
        )


class _FakeBoxdClient:
    """Stand-in for ``boxd.AsyncBoxd`` used as an async context manager."""

    def __init__(self):
        self.machines = _FakeMachines()
        self.snapshots = MagicMock()
        self.disks = MagicMock()
        self.close = AsyncMock()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        await self.close()


@pytest.fixture
def fake_machine():
    """Return a fresh _FakeMachine per test."""
    return _FakeMachine()


@pytest.fixture
def fake_client(fake_machine):
    """Return a fresh _FakeBoxdClient wired so machine lookups resolve.

    ``files.upload`` confirms the full byte count by default, matching a
    clean upload.
    """
    c = _FakeBoxdClient()
    c.machines.create.return_value = fake_machine
    c.machines.get.return_value = fake_machine
    c.machines.wait_until_ready.return_value = fake_machine

    async def _upload_ok(machine_id, path, data):
        return len(data)

    c.machines.files.upload.side_effect = _upload_ok
    return c


@pytest.fixture
def mock_boxd(monkeypatch, fake_client):
    """Patch boxd_provider._make_client to return `fake_client`."""
    import bindu.runtime.boxd_provider as bp

    monkeypatch.setattr(bp, "_make_client", lambda **kw: fake_client)
    return fake_client
