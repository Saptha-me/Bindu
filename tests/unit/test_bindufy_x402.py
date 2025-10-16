"""Unit tests for bindufy x402 capability injection."""

import pytest

from bindu.penguin.bindufy import _update_capabilities_with_x402
from bindu.settings import app_settings

pytestmark = pytest.mark.x402


class TestBindufyX402:
    def test_appends_extension_when_none(self):
        caps = _update_capabilities_with_x402(None)
        exts = caps.get("extensions") or []
        assert any(e.get("uri") == app_settings.x402.extension_uri for e in exts)

    def test_appends_extension_to_existing(self):
        caps = _update_capabilities_with_x402({"streaming": True, "extensions": []})
        exts = caps.get("extensions") or []
        assert any(e.get("uri") == app_settings.x402.extension_uri for e in exts)
