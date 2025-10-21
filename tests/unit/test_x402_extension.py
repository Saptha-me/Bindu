"""Unit tests for x402 extension helpers."""

import pytest
from typing import List, Tuple

from starlette.requests import Request
from starlette.responses import Response

from bindu.extensions.x402.extension import (
    add_activation_header,
    get_agent_extension,
    is_activation_requested,
)
from bindu.settings import app_settings

pytestmark = pytest.mark.x402


def _make_request_with_headers(headers: dict[str, str]) -> Request:
    raw_headers: List[Tuple[bytes, bytes]] = [
        (k.lower().encode("latin-1"), v.encode("latin-1")) for k, v in headers.items()
    ]
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": raw_headers,
    }

    async def _receive():  # pragma: no cover - not used in these tests
        return {"type": "http.request", "body": b""}

    return Request(scope, _receive)


class TestX402ExtensionHelpers:
    def test_get_agent_extension_defaults(self):
        ext = get_agent_extension()
        assert ext["uri"] == app_settings.x402.extension_uri
        assert ext.get("required") is False
        assert "Supports x402 A2A agent payments" in ext.get("description", "")

    def test_get_agent_extension_overrides(self):
        ext = get_agent_extension(required=True, description="custom")
        assert ext["uri"] == app_settings.x402.extension_uri
        assert ext.get("required") is True
        assert ext.get("description") == "custom"

    def test_is_activation_requested_true(self):
        req = _make_request_with_headers(
            {
                "X-A2A-Extensions": app_settings.x402.extension_uri,
            }
        )
        assert is_activation_requested(req) is True

    def test_is_activation_requested_false(self):
        req = _make_request_with_headers(
            {"X-A2A-Extensions": "https://example.com/ext"}
        )
        assert is_activation_requested(req) is False

    def test_add_activation_header_sets_header(self):
        resp = Response(content=b"ok")
        resp = add_activation_header(resp)
        assert resp.headers.get("X-A2A-Extensions") == app_settings.x402.extension_uri
