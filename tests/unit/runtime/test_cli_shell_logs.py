"""Tests for ``bindu shell <agent>`` and ``bindu logs <agent>``."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_logs_streams_to_stdout(capsys):
    """`bindu logs my-agent` tails the in-VM agent log and pipes to stdout.

    Server-side ``StreamLogs`` is unimplemented in boxd 0.1.x; the CLI
    works around it by ``tail -F``-ing the known agent log path inside
    the VM via a streaming exec.
    """
    from bindu.cli import _handle_logs

    chunks = [b"hello\n", b"world\n"]

    class _Stdout:
        def __init__(self, cs):
            self._cs = list(cs)

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self._cs:
                raise StopAsyncIteration
            return self._cs.pop(0)

    fake_proc = MagicMock()
    fake_proc.stdout = _Stdout(chunks)

    fake_box = MagicMock()
    fake_box.exec = AsyncMock(return_value=fake_proc)

    fake_compute = MagicMock()
    fake_compute.box.get = AsyncMock(return_value=fake_box)
    fake_compute.__aenter__ = AsyncMock(return_value=fake_compute)
    fake_compute.__aexit__ = AsyncMock()

    with patch("bindu.runtime.boxd_provider._make_compute", return_value=fake_compute):
        await _handle_logs("my-agent", follow=True)

    out = capsys.readouterr().out
    assert "hello" in out
    assert "world" in out
    call = fake_box.exec.await_args
    assert call is not None, "await_args should not be None"
    assert call.kwargs.get("stream") is True
    assert "-F" in call.args  # follow=True → tail -F


@pytest.mark.asyncio
async def test_shell_calls_exec_bash():
    """`bindu shell my-agent` should exec `bash` interactively on the VM."""
    from bindu.cli import _handle_shell

    fake_box = MagicMock()
    fake_box.exec = AsyncMock()

    fake_compute = MagicMock()
    fake_compute.box.get = AsyncMock(return_value=fake_box)
    fake_compute.__aenter__ = AsyncMock(return_value=fake_compute)
    fake_compute.__aexit__ = AsyncMock()

    with patch("bindu.runtime.boxd_provider._make_compute", return_value=fake_compute):
        await _handle_shell("my-agent")

    fake_box.exec.assert_awaited_once()
    args = fake_box.exec.await_args
    assert args is not None, "await_args should not be None"
    assert "bash" in args.args
    assert args.kwargs.get("interactive") is True
