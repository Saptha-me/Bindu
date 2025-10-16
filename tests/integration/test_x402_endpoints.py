"""Tests that x402 extension header is echoed by endpoints.

These directly call the endpoint functions with minimal fake app objects to avoid heavy setup.
"""

import json
from uuid import UUID
from types import SimpleNamespace

import pytest
from starlette.requests import Request

from bindu.server.endpoints.a2a_protocol import agent_run_endpoint
from bindu.server.endpoints.agent_card import agent_card_endpoint
from bindu.settings import app_settings

pytestmark = [pytest.mark.integration, pytest.mark.x402]


def _make_request(method: str = "GET", path: str = "/", headers: dict | None = None, body: bytes | None = None) -> Request:
    raw_headers = []
    for k, v in (headers or {}).items():
        raw_headers.append((k.lower().encode("latin-1"), v.encode("latin-1")))
    scope = {"type": "http", "method": method, "path": path, "headers": raw_headers}

    async def _receive():  # pragma: no cover - simple receive impl
        return {"type": "http.request", "body": body or b""}

    return Request(scope, _receive)


def test_agent_card_echoes_extension_header():
    # Minimal fake app with required attributes for agent_card_endpoint
    fake_manifest = SimpleNamespace(
        id=UUID(int=1),
        name="test",
        description="",
        url="http://localhost",
        version="1.0.0",
        skills=[],
        capabilities={},
        kind="agent",
        num_history_sessions=1,
        extra_data={},
        debug_mode=False,
        debug_level=1,
        monitoring=False,
        telemetry=False,
        agent_trust={"identity_provider": "custom", "inherited_roles": [], "creator_id": "x", "creation_timestamp": 0, "trust_verification_required": False, "allowed_operations": {}},
    )
    app = SimpleNamespace(
        manifest=fake_manifest,
        url="http://localhost",
        version="1.0.0",
        _agent_card_json_schema=None,
    )

    req = _make_request(headers={"X-A2A-Extensions": app_settings.x402.extension_uri})
    resp = asyncio_run(agent_card_endpoint(app, req))
    assert resp.headers.get("X-A2A-Extensions") == app_settings.x402.extension_uri


def test_agent_run_echoes_extension_header():
    class FakeTM:
        async def list_tasks(self, request):  # noqa: ARG002
            return {"jsonrpc": "2.0", "id": str(UUID(int=1)), "result": []}

    app = SimpleNamespace(task_manager=FakeTM())
    body = json.dumps({
        "jsonrpc": "2.0",
        "id": str(UUID(int=1)),
        "method": "tasks/list",
        "params": {},
    }).encode()

    req = _make_request(method="POST", headers={"X-A2A-Extensions": app_settings.x402.extension_uri}, body=body)
    resp = asyncio_run(agent_run_endpoint(app, req))
    assert resp.headers.get("X-A2A-Extensions") == app_settings.x402.extension_uri


def asyncio_run(coro):
    try:
        import asyncio

        return asyncio.get_event_loop().run_until_complete(coro)
    except RuntimeError:
        # When no loop is running, create a new one
        import asyncio as _asyncio

        loop = _asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
