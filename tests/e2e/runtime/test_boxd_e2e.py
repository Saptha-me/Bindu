"""Real-boxd-VM e2e for the runtime provider.

Skipped unless ``BOXD_E2E=1`` and ``BOXD_API_KEY`` (or ``BOXD_TOKEN``) is set.
This test creates a real VM, ships a tiny echo agent, hits the A2A endpoint,
and destroys the VM. Slow (~30–60s), costs real boxd resources.
"""

import asyncio
import os
import uuid
from pathlib import Path

import httpx
import pytest

from bindu.runtime import RuntimeConfig
from bindu.runtime.boxd_provider import BoxdRuntimeProvider

pytestmark = [
    pytest.mark.boxd_e2e,
    pytest.mark.skipif(
        os.environ.get("BOXD_E2E") != "1",
        reason="set BOXD_E2E=1 to enable",
    ),
    pytest.mark.skipif(
        not (os.environ.get("BOXD_API_KEY") or os.environ.get("BOXD_TOKEN")),
        reason="BOXD_API_KEY or BOXD_TOKEN required",
    ),
]


@pytest.mark.asyncio
async def test_full_lifecycle(tmp_path):
    """Deploy → A2A request → assert echo → destroy."""
    fixture_src = Path(__file__).parent / "echo_agent.py"
    (tmp_path / "echo_agent.py").write_text(fixture_src.read_text())
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "boxd-e2e-echo"\nversion = "0.1.0"\n'
    )

    p = BoxdRuntimeProvider()
    cfg = RuntimeConfig.from_dict(
        {
            "provider": "boxd",
            # Plenty of headroom so the deploy → install → start sequence
            # doesn't race the auto-suspend timer.
            "auto_suspend": 600,
        }
    )

    handle = None
    try:
        handle = await p.deploy(
            agent_name="boxd-e2e-echo",
            source_dir=tmp_path,
            config=cfg,
        )
        assert handle.url

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Health check confirms reachability + correct port routing.
            resp = await client.get(handle.url + "/health")
            assert resp.status_code == 200, resp.text

            # Agent card proves the bindu app (not the boxd "waiting"
            # placeholder) is what's responding, and that the manifest's
            # name matches what we deployed.
            resp = await client.get(handle.url + "/.well-known/agent.json")
            assert resp.status_code == 200, resp.text
            card = resp.json()
            assert card.get("name") == "boxd-e2e-echo", card

            # Exercise the actual message path: without this, a history
            # contract regression (e.g. re-flattening parts) keeps the
            # e2e green while every deployed echo returns empty output.
            task_id, context_id = str(uuid.uuid4()), str(uuid.uuid4())
            resp = await client.post(
                handle.url + "/",
                json={
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "message/send",
                    "params": {
                        "configuration": {"accepted_output_modes": ["text"]},
                        "message": {
                            "role": "user",
                            "kind": "message",
                            "parts": [{"kind": "text", "text": "boxd echo probe"}],
                            "messageId": str(uuid.uuid4()),
                            "contextId": context_id,
                            "taskId": task_id,
                        },
                    },
                },
            )
            assert resp.status_code == 200, resp.text

            # Poll until terminal, then require the echoed text — the
            # fixture reads parts (with a content fallback for older
            # PyPI releases inside the VM), so either code path must
            # surface the probe text, never an empty echo.
            reply = ""
            for _ in range(40):
                resp = await client.post(
                    handle.url + "/",
                    json={
                        "jsonrpc": "2.0",
                        "id": str(uuid.uuid4()),
                        "method": "tasks/get",
                        "params": {"taskId": task_id},
                    },
                )
                task = resp.json().get("result") or {}
                state = (task.get("status") or {}).get("state")
                if state in ("completed", "failed", "rejected"):
                    assert state == "completed", task
                    chunks = [
                        p.get("text", "")
                        for art in task.get("artifacts") or []
                        for p in art.get("parts") or []
                        if p.get("kind") == "text"
                    ]
                    reply = " ".join(chunks)
                    break
                await asyncio.sleep(0.5)
            assert "boxd echo probe" in reply, f"echo lost the message text: {reply!r}"
    finally:
        if handle is not None:
            await p.on_exit(handle, "destroy")
