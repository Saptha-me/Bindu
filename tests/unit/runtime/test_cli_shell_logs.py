"""Tests for ``bindu shell <agent>`` and ``bindu logs <agent>``."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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


def _fake_client(machine, stream):
    client = MagicMock()
    client.machines.get = AsyncMock(return_value=machine)
    client.machines.stream_exec = MagicMock(return_value=stream)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_logs_streams_to_stdout(capsys):
    """`bindu logs my-agent` tails the in-VM agent log and pipes to stdout.

    ``machines.logs`` is the VM console, which a detached nohup'd agent
    never writes to — the CLI ``tail -F``s the known agent log path inside
    the VM via a streaming exec instead.
    """
    from bindu.cli import _handle_logs

    machine = MagicMock(id="vm-1")
    stream = _FakeStream([b"hello\n", b"world\n"])
    client = _fake_client(machine, stream)

    with patch("bindu.runtime.boxd_provider._make_client", return_value=client):
        await _handle_logs("my-agent", follow=True)

    out = capsys.readouterr().out
    assert "hello" in out
    assert "world" in out
    call = client.machines.stream_exec.call_args
    assert call is not None
    assert call.args[0] == "vm-1"
    command = call.kwargs.get("command")
    assert command[0] == "tail"
    assert "-F" in command  # follow=True → tail -F


@pytest.mark.asyncio
async def test_shell_opens_tty_bash_session():
    """`bindu shell my-agent` opens a tty ``stream_exec`` bash session."""
    from bindu.cli import _handle_shell

    machine = MagicMock(id="vm-1")
    stream = _FakeStream([b"$ \n"])
    client = _fake_client(machine, stream)

    with patch("bindu.runtime.boxd_provider._make_client", return_value=client):
        await _handle_shell("my-agent")

    client.machines.get.assert_awaited_once_with("my-agent")
    call = client.machines.stream_exec.call_args
    assert call is not None
    assert call.args[0] == "vm-1"
    assert call.kwargs.get("command") == "bash"
    assert call.kwargs.get("tty") is True
    assert stream.closed
