"""Unit tests for ManifestWorker x402 payment flow using monkeypatches.

This test stubs external dependencies (opentelemetry, x402) to avoid heavy installs.
"""

from types import SimpleNamespace, ModuleType
from typing import cast
import sys

import pytest

pytestmark = pytest.mark.x402

# --- Minimal stubs only for x402 to avoid heavy deps (opentelemetry stub is provided in conftest) ---

# Stub x402 modules so worker import succeeds
x402_mod = ModuleType("x402")
x402_types = ModuleType("x402.types")
x402_fac = ModuleType("x402.facilitator")
sys.modules["x402"] = x402_mod
sys.modules["x402.types"] = x402_types
sys.modules["x402.facilitator"] = x402_fac

from bindu.common.models import AgentManifest
from bindu.common.protocol.types import TaskSendParams
from bindu.server.workers.manifest_worker import ManifestWorker
from bindu.settings import app_settings
from tests.mocks import MockAgent, MockManifest
from tests.utils import assert_task_state, create_test_message


class _FakeVerifyResp:
    def __init__(self, is_valid: bool, invalid_reason: str | None = None):
        self.is_valid = is_valid
        self.invalid_reason = invalid_reason


class _FakeSettleResp:
    def __init__(self, success: bool, error_reason: str | None = None, payload: dict | None = None):
        self.success = success
        self.error_reason = error_reason
        self._payload = payload or {"ok": True}

    def model_dump(self, by_alias: bool = True):
        return self._payload


def _setup_task_with_payment_metadata(storage, status: str):
    meta = {
        app_settings.x402.meta_status_key: status,
        app_settings.x402.meta_payload_key: {"dummy": True},
        app_settings.x402.meta_required_key: {"accepts": [{"scheme": "exact", "network": "base"}]},
    }
    message = create_test_message(text="Pay", metadata=meta)
    return storage.submit_task(message["context_id"], message)


@pytest.mark.asyncio
async def test_verify_failure_sets_input_required(monkeypatch, storage, scheduler):
    agent = MockAgent(response="done")
    manifest = MockManifest(agent_fn=agent)
    worker = ManifestWorker(scheduler=scheduler, storage=storage, manifest=cast(AgentManifest, manifest))

    # Patch x402 parsing to bypass real models
    monkeypatch.setattr(ManifestWorker, "_parse_payment_payload", lambda self, data: SimpleNamespace(scheme="exact", network="base"))
    monkeypatch.setattr(ManifestWorker, "_select_requirement_from_required", lambda self, required, payload: SimpleNamespace())

    class FakeFacilitator:
        async def verify(self, payload, req):
            return _FakeVerifyResp(is_valid=False, invalid_reason="bad")

    monkeypatch.setattr("bindu.server.workers.manifest_worker.FacilitatorClient", FakeFacilitator)

    task = await _setup_task_with_payment_metadata(storage, app_settings.x402.status_submitted)
    params = cast(TaskSendParams, {"task_id": task["id"], "context_id": task["context_id"], "message": task["history"][0]})
    await worker.run_task(params)

    updated = await storage.load_task(task["id"])
    assert_task_state(updated, "input-required")
    assert updated.get("metadata", {}).get(app_settings.x402.meta_status_key) == app_settings.x402.status_failed


@pytest.mark.asyncio
async def test_verify_ok_settle_ok_completes_with_receipt(monkeypatch, storage, scheduler):
    agent = MockAgent(response="result")
    manifest = MockManifest(agent_fn=agent)
    worker = ManifestWorker(scheduler=scheduler, storage=storage, manifest=cast(AgentManifest, manifest))

    monkeypatch.setattr(ManifestWorker, "_parse_payment_payload", lambda self, data: SimpleNamespace(scheme="exact", network="base"))
    monkeypatch.setattr(ManifestWorker, "_select_requirement_from_required", lambda self, required, payload: SimpleNamespace())

    class FakeFacilitator:
        async def verify(self, payload, req):
            return _FakeVerifyResp(is_valid=True)

        async def settle(self, payload, req):
            return _FakeSettleResp(success=True, payload={"receipt": "ok"})

    monkeypatch.setattr("bindu.server.workers.manifest_worker.FacilitatorClient", FakeFacilitator)

    task = await _setup_task_with_payment_metadata(storage, app_settings.x402.status_submitted)
    params = cast(TaskSendParams, {"task_id": task["id"], "context_id": task["context_id"], "message": task["history"][0]})
    await worker.run_task(params)

    updated = await storage.load_task(task["id"])
    assert_task_state(updated, "completed")
    assert updated.get("metadata", {}).get(app_settings.x402.meta_status_key) == app_settings.x402.status_completed
    receipts = updated.get("metadata", {}).get(app_settings.x402.meta_receipts_key) or []
    assert len(receipts) == 1


@pytest.mark.asyncio
async def test_verify_ok_settle_fail_sets_input_required(monkeypatch, storage, scheduler):
    agent = MockAgent(response="result")
    manifest = MockManifest(agent_fn=agent)
    worker = ManifestWorker(scheduler=scheduler, storage=storage, manifest=cast(AgentManifest, manifest))

    monkeypatch.setattr(ManifestWorker, "_parse_payment_payload", lambda self, data: SimpleNamespace(scheme="exact", network="base"))
    monkeypatch.setattr(ManifestWorker, "_select_requirement_from_required", lambda self, required, payload: SimpleNamespace())

    class FakeFacilitator:
        async def verify(self, payload, req):
            return _FakeVerifyResp(is_valid=True)

        async def settle(self, payload, req):
            return _FakeSettleResp(success=False, error_reason="no_funds", payload={"ok": False})

    monkeypatch.setattr("bindu.server.workers.manifest_worker.FacilitatorClient", FakeFacilitator)

    task = await _setup_task_with_payment_metadata(storage, app_settings.x402.status_submitted)
    params = cast(TaskSendParams, {"task_id": task["id"], "context_id": task["context_id"], "message": task["history"][0]})
    await worker.run_task(params)

    updated = await storage.load_task(task["id"])
    assert_task_state(updated, "input-required")
    assert updated.get("metadata", {}).get(app_settings.x402.meta_status_key) == app_settings.x402.status_failed


@pytest.mark.asyncio
async def test_verify_raises_sets_input_required(monkeypatch, storage, scheduler):
    agent = MockAgent(response="result")
    manifest = MockManifest(agent_fn=agent)
    worker = ManifestWorker(scheduler=scheduler, storage=storage, manifest=cast(AgentManifest, manifest))

    monkeypatch.setattr(ManifestWorker, "_parse_payment_payload", lambda self, data: SimpleNamespace(scheme="exact", network="base"))
    monkeypatch.setattr(ManifestWorker, "_select_requirement_from_required", lambda self, required, payload: SimpleNamespace())

    class FakeFacilitator:
        async def verify(self, payload, req):
            raise RuntimeError("boom")

    monkeypatch.setattr("bindu.server.workers.manifest_worker.FacilitatorClient", FakeFacilitator)

    task = await _setup_task_with_payment_metadata(storage, app_settings.x402.status_submitted)
    params = cast(TaskSendParams, {"task_id": task["id"], "context_id": task["context_id"], "message": task["history"][0]})
    await worker.run_task(params)

    updated = await storage.load_task(task["id"])
    assert_task_state(updated, "input-required")
