"""End-to-end exercise of all four x402 settle-ordering scenarios from #562.

This is a real integration test, not a unit test:
- Real X402Middleware in front of a stub agent endpoint (for replay/scenario 4)
- Real ManifestWorker driving the full task pipeline
- Real InMemoryStorage as the task backing store
- Real InMemoryNonceStore for replay defense
- Mock facilitator (HTTPFacilitatorClient, x402ResourceServer) so we can
  inject each failure mode deterministically

Run with ``uv run pytest -s tests/integration/x402/test_e2e_scenarios.py``
to see the per-scenario trace output that mirrors the diagrams in
``docs/PAYMENT.md`` and the PR descriptions for #563 / #564.
"""

from __future__ import annotations

import asyncio
import base64
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import httpx
import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from x402 import PaymentPayload, PaymentRequirements
from x402.schemas.responses import VerifyResponse

from bindu.common.models import AgentManifest
from bindu.server.endpoints.a2a_protocol import agent_run_endpoint
from bindu.server.middleware.x402.nonce_store import InMemoryNonceStore
from bindu.server.middleware.x402.x402_middleware import X402Middleware
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.task_manager import TaskManager
from bindu.server.workers.manifest_worker import ManifestWorker
from bindu.settings import app_settings
from bindu.utils.logging import get_logger


pytestmark = [
    pytest.mark.integration,
    pytest.mark.e2e,
    pytest.mark.slow,
    pytest.mark.x402,
]

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Shared test fixtures: a single canonical payment requirement and a helper
# to build EIP-3009-shaped payloads with parameterised nonces / payers.
# ---------------------------------------------------------------------------

REQUIREMENT = PaymentRequirements(
    scheme="exact",
    network="eip155:84532",
    asset="0x036cbd53842c5426634e7929541ec2318f3dcf7e",
    amount="1000000",  # 1 USDC (6 decimals)
    pay_to="0xa11ce0000000000000000000000000000000a11ce",
    max_timeout_seconds=60,
    extra={"name": "USDC", "version": "2"},
)


def make_payload(
    nonce: str, payer: str = "0xb0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0"
) -> PaymentPayload:
    """Build a syntactically valid EIP-3009 payload for the canonical requirement."""
    return PaymentPayload(
        x402_version=2,
        payload={
            "signature": "0x" + "00" * 65,
            "authorization": {
                "from": payer,
                "to": REQUIREMENT.pay_to,
                "value": REQUIREMENT.amount,
                "validAfter": "0",
                "validBefore": "9999999999",
                "nonce": nonce,
            },
        },
        accepted=REQUIREMENT,
    )


def payment_header(payload: PaymentPayload) -> str:
    """base64 encode a payload the way real clients send it."""
    return base64.b64encode(payload.model_dump_json(by_alias=True).encode()).decode()


def payment_context_for(payload: PaymentPayload) -> dict[str, Any]:
    """Build the payment_context dict the middleware would attach to a task."""
    return {
        "payment_payload": payload.model_dump(by_alias=True),
        "payment_requirements": REQUIREMENT.model_dump(by_alias=True),
        "verify_response": {"is_valid": True, "invalid_reason": None},
    }


# ---------------------------------------------------------------------------
# Worker harness used for scenarios 1, 2, 3 — drives run_task end-to-end
# against the real worker with InMemoryStorage and a mocked facilitator.
# ---------------------------------------------------------------------------


class ManifestRunRecorder:
    """A stand-in for an agent that records every call to .run().

    Used to assert in each scenario whether the LLM call was actually
    invoked. Returns a fixed deliverable on the happy path.
    """

    def __init__(self, name: str = "test-agent", raises: BaseException | None = None):
        self.name = name
        self.did_extension = MagicMock()
        self.did_extension.did = "did:example:agent"
        self.x402_extension = MagicMock()
        self.enable_system_message = False
        self.enable_context_based_history = False
        self._raises = raises
        self.calls: list[list[dict[str, Any]]] = []

    def run(self, messages: list[dict[str, Any]]) -> str:
        self.calls.append(messages)
        if self._raises is not None:
            raise self._raises
        return "Summary: contract terminates 2027-01-31, ..."


async def submit_and_drive_task(
    *,
    storage: InMemoryStorage,
    manifest: ManifestRunRecorder,
    context_id: UUID,
    settle_outcome: dict[str, Any] | type[BaseException] | BaseException,
    payment_context: dict[str, Any] | None,
    expect_raises: type[BaseException] | None = None,
) -> UUID:
    """Submit a task to storage and drive it through run_task end-to-end.

    ``settle_outcome`` is either:
      - a dict — the value to return from facilitator.settle() as a
        ``SettleResponse``-like mock (with .success / .error_reason)
      - an Exception class or instance — to raise from facilitator.settle()
    """
    task_id = uuid4()
    message = {
        "task_id": task_id,
        "context_id": context_id,
        "message_id": uuid4(),
        "role": "user",
        "parts": [{"kind": "text", "text": "summarize this contract"}],
        "history": [],
    }
    await storage.submit_task(context_id, message)  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]

    worker = ManifestWorker(
        manifest=manifest,  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]
        scheduler=MagicMock(),
        storage=storage,
    )

    # Patch the facilitator at the boundary _settle_payment uses.
    with (
        patch("x402.PaymentPayload") as mock_pp,
        patch("x402.PaymentRequirements") as mock_pr,
        patch(
            "bindu.server.workers.manifest_worker.HTTPFacilitatorClient"
        ) as mock_fac_class,
    ):
        mock_pp.model_validate = MagicMock(return_value=MagicMock())
        mock_pr.model_validate = MagicMock(return_value=MagicMock())

        mock_fac = AsyncMock()
        if isinstance(settle_outcome, (BaseException, type)) and (
            isinstance(settle_outcome, BaseException)
            or issubclass(settle_outcome, BaseException)
        ):
            mock_fac.settle = AsyncMock(side_effect=settle_outcome)
        else:
            response = MagicMock()
            response.success = settle_outcome["success"]
            response.error_reason = settle_outcome.get("error_reason")
            response.model_dump = MagicMock(return_value=settle_outcome)
            mock_fac.settle = AsyncMock(return_value=response)
        mock_fac_class.return_value = mock_fac

        params: dict[str, Any] = {"task_id": task_id, "context_id": context_id}
        if payment_context is not None:
            params["payment_context"] = payment_context

        if expect_raises is not None:
            with pytest.raises(expect_raises):
                await worker.run_task(params)  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]
        else:
            await worker.run_task(params)  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]

    return task_id


def describe(label: str) -> None:
    """Pretty-print a scenario header."""
    print()
    print("─" * 78)
    print(label)
    print("─" * 78)


def report_task(task: Any, manifest_call_count: int) -> None:
    """Pretty-print the end state of a task."""
    state = task["status"]["state"]
    meta = task.get("metadata") or {}
    print(f"  → task state:           {state}")
    print(f"  → manifest.run calls:   {manifest_call_count}")
    print(f"  → payment status:       {meta.get('x402.payment.status', '(none)')}")
    if meta.get("x402_nonce"):
        print(f"  → recovery nonce:       {meta['x402_nonce']}")
    if meta.get("x402_authorization"):
        print(f"  → recovery from-addr:   {meta['x402_authorization'].get('from')}")
    artifacts = task.get("artifacts") or []
    print(f"  → artifacts delivered:  {len(artifacts)}")


async def wait_for_terminal_task(
    storage: InMemoryStorage,
    task_id: UUID,
    *,
    timeout_seconds: float = 2.0,
) -> Any:
    """Poll in-memory storage until the background worker reaches a terminal state."""
    terminal_states = set(app_settings.agent.terminal_states)
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    last_state = "(not created)"

    while asyncio.get_running_loop().time() < deadline:
        task = await storage.load_task(task_id)
        if task is not None:
            last_state = task["status"]["state"]
            if last_state in terminal_states:
                return task
        await asyncio.sleep(0.01)

    pytest.fail(
        f"Task {task_id} did not reach a terminal state; last state={last_state}"
    )


# ---------------------------------------------------------------------------
# Scenario 1: Front-run drain (Mallory empties wallet between verify and settle)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario_1_front_run_drain():
    describe("Scenario 1: Mallory drains wallet between verify and settle")
    print("  Verify said OK; before settle, payer balance went to 0.")
    print("  Facilitator.settle returns success=False, error='reverted'.")

    storage = InMemoryStorage()
    manifest = ManifestRunRecorder()

    task_id = await submit_and_drive_task(
        storage=storage,
        manifest=manifest,
        context_id=uuid4(),
        settle_outcome={
            "success": False,
            "error_reason": "transfer reverted: insufficient balance",
        },
        payment_context=payment_context_for(
            make_payload(
                nonce="0x" + "ab" * 32,
                payer="0xMa11ory0000000000000000000000000000a11ory",
            )
        ),
    )

    task = await storage.load_task(task_id)
    assert task is not None
    report_task(task, len(manifest.calls))

    # Settle-first means LLM never ran.
    assert len(manifest.calls) == 0, "manifest.run must not be called when settle fails"
    # Task ends in failed; no artifact was delivered.
    assert task["status"]["state"] == "failed"
    assert not task.get("artifacts")
    # Recovery metadata is persisted so an operator can audit.
    meta = task.get("metadata") or {}
    assert meta.get("x402.payment.status") == "payment-failed"
    assert meta.get("x402_nonce") == "0x" + "ab" * 32


# ---------------------------------------------------------------------------
# Scenario 2: Settle timeout (facilitator hangs, can't tell if tx confirmed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario_2_settle_timeout():
    describe("Scenario 2: facilitator times out during settle")
    print("  Verify said OK; facilitator.settle raises TimeoutError.")
    print("  We may or may not have actually settled on-chain — unknown.")

    storage = InMemoryStorage()
    manifest = ManifestRunRecorder()

    task_id = await submit_and_drive_task(
        storage=storage,
        manifest=manifest,
        context_id=uuid4(),
        settle_outcome=asyncio.TimeoutError("upstream facilitator timeout"),
        payment_context=payment_context_for(
            make_payload(
                nonce="0x" + "cd" * 32,
                payer="0xCar01000000000000000000000000000000ar01",
            )
        ),
    )

    task = await storage.load_task(task_id)
    assert task is not None
    report_task(task, len(manifest.calls))

    # Even on exception, settle-first never runs the LLM.
    assert len(manifest.calls) == 0
    assert task["status"]["state"] == "failed"
    # Reconciliation metadata is the whole point of this scenario.
    meta = task.get("metadata") or {}
    assert meta.get("x402_nonce") == "0x" + "cd" * 32
    assert (
        meta.get("x402_authorization", {}).get("from")
        == "0xCar01000000000000000000000000000000ar01"
    )
    print("  → reconciliation worker can now query the chain for this nonce.")


# ---------------------------------------------------------------------------
# Scenario 3: Parallel-nonce double-spend (Bob sends two requests with different nonces)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario_3_parallel_nonce_double_spend():
    describe("Scenario 3: parallel requests with different nonces")
    print("  Bob has $1 USDC; sends two requests in parallel with nonces A and B.")
    print("  Both pass verify (balance check is non-reserving).")
    print("  Race at /settle: first wins (success), second reverts.")

    storage = InMemoryStorage()
    # Two separate manifest recorders so we can attribute calls per task.
    manifest_a = ManifestRunRecorder(name="worker-a")
    manifest_b = ManifestRunRecorder(name="worker-b")
    context_id = uuid4()

    task_id_a = await submit_and_drive_task(
        storage=storage,
        manifest=manifest_a,
        context_id=context_id,
        settle_outcome={"success": True, "tx_hash": "0xfirstwin"},
        payment_context=payment_context_for(
            make_payload(
                nonce="0x" + "a1" * 32,
                payer="0xB0b00000000000000000000000000000000000b0",
            )
        ),
    )

    task_id_b = await submit_and_drive_task(
        storage=storage,
        manifest=manifest_b,
        context_id=context_id,
        settle_outcome={
            "success": False,
            "error_reason": "transfer reverted: insufficient balance",
        },
        payment_context=payment_context_for(
            make_payload(
                nonce="0x" + "b2" * 32,
                payer="0xB0b00000000000000000000000000000000000b0",
            )
        ),
    )

    task_a = await storage.load_task(task_id_a)
    task_b = await storage.load_task(task_id_b)
    assert task_a is not None and task_b is not None

    print("  Task A (settle won):")
    report_task(task_a, len(manifest_a.calls))
    print("  Task B (settle lost):")
    report_task(task_b, len(manifest_b.calls))

    # Task A: settled, ran, delivered.
    assert task_a["status"]["state"] == "completed"
    assert len(manifest_a.calls) == 1
    assert task_a.get("artifacts")
    # Task B: settle lost the race, NO LLM call burned.
    assert task_b["status"]["state"] == "failed"
    assert len(manifest_b.calls) == 0
    assert not task_b.get("artifacts")
    print("  → net: 1 LLM call (paid), 0 LLM calls wasted, 1 artifact delivered.")


# ---------------------------------------------------------------------------
# Full paid HTTP lifecycle: middleware -> A2A endpoint -> scheduler -> worker
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_http_paid_message_send_settles_and_completes():
    describe("Full HTTP paid message/send lifecycle")
    logger.info("Real ASGI request enters X402Middleware and agent_run_endpoint.")
    logger.info(
        "Payment context must reach ManifestWorker, settle, and complete the task."
    )

    storage = InMemoryStorage()
    scheduler = InMemoryScheduler()
    manifest = ManifestRunRecorder(name="paid-agent")

    resource_server = MagicMock()
    resource_server.find_matching_requirements = MagicMock(return_value=REQUIREMENT)
    resource_server.verify_payment = AsyncMock(
        return_value=VerifyResponse(
            is_valid=True,
            invalid_reason=None,
            payer="0xB0b00000000000000000000000000000000000b0",
        )
    )

    settle_response = MagicMock()
    settle_response.success = True
    settle_response.error_reason = None
    settle_response.model_dump = MagicMock(
        return_value={"success": True, "transaction": "0xpaidsettled"}
    )

    original_methods = app_settings.x402.protected_methods
    app_settings.x402.protected_methods = ["message/send"]
    try:
        async with TaskManager(
            scheduler=scheduler,
            storage=storage,
            manifest=manifest,  # type: ignore[arg-type]
        ) as manager:
            endpoint_app = SimpleNamespace(task_manager=manager)

            async def endpoint(request: Request):
                return await agent_run_endpoint(cast(Any, endpoint_app), request)

            asgi_app = Starlette(
                routes=[Route("/", endpoint, methods=["POST"])],
                middleware=[
                    Middleware(
                        X402Middleware,
                        manifest=cast(AgentManifest, manifest),
                        resource_server=resource_server,
                        x402_ext=manifest.x402_extension,
                        payment_requirements=[REQUIREMENT],
                        nonce_store=InMemoryNonceStore(),
                    )
                ],
            )

            task_id = uuid4()
            context_id = uuid4()
            request_id = str(uuid4())
            request_body = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "message/send",
                "params": {
                    "configuration": {
                        "acceptedOutputModes": ["text/plain"],
                    },
                    "message": {
                        "messageId": str(uuid4()),
                        "contextId": str(context_id),
                        "taskId": str(task_id),
                        "kind": "message",
                        "role": "user",
                        "parts": [
                            {
                                "kind": "text",
                                "text": "summarize this contract",
                            }
                        ],
                    },
                },
            }
            payload = make_payload(nonce="0x" + "fa" * 32)

            with patch(
                "bindu.server.workers.manifest_worker.HTTPFacilitatorClient"
            ) as mock_fac_class:
                mock_fac = AsyncMock()
                mock_fac.settle = AsyncMock(return_value=settle_response)
                mock_fac_class.return_value = mock_fac

                transport = httpx.ASGITransport(app=asgi_app)
                async with httpx.AsyncClient(
                    transport=transport,
                    base_url="http://testserver",
                    timeout=2.0,
                ) as client:
                    response = await client.post(
                        "/",
                        json=request_body,
                        headers={"X-PAYMENT": payment_header(payload)},
                    )

                assert response.status_code == 200, response.text
                response_json = response.json()
                assert response_json["id"] == request_id
                assert response_json["result"]["id"] == str(task_id)

                task = await wait_for_terminal_task(storage, task_id)

    finally:
        app_settings.x402.protected_methods = original_methods

    report_task(task, len(manifest.calls))

    assert task["status"]["state"] == "completed"
    assert len(manifest.calls) == 1
    assert task.get("artifacts")

    history_metadata = task["history"][0].get("metadata") or {}
    assert "_payment_context" not in history_metadata

    meta = task.get("metadata") or {}
    assert (
        meta.get(app_settings.x402.meta_status_key)
        == app_settings.x402.status_completed
    )
    assert meta.get(app_settings.x402.meta_receipts_key) == [
        {"success": True, "transaction": "0xpaidsettled"}
    ]

    resource_server.verify_payment.assert_awaited_once()
    mock_fac.settle.assert_awaited_once()
    settle_call = mock_fac.settle.await_args
    assert settle_call is not None
    settled_payload, settled_requirement = settle_call.args
    assert settled_payload.payload["authorization"]["nonce"] == "0x" + "fa" * 32
    assert settled_requirement.network == REQUIREMENT.network


# ---------------------------------------------------------------------------
# Scenario 4: Replay (identical nonce sent twice) — middleware-level defense
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario_4_replay_rejected_at_middleware():
    describe("Scenario 4: Mallory replays the same X-PAYMENT header")
    print("  Same (network, asset, nonce) presented twice within validBefore.")
    print("  Expected: middleware claims the nonce on the first request and")
    print("  rejects the second one with 402 BEFORE it ever reaches verify.")

    # Build an isolated app: real X402Middleware in front of a stub agent.
    nonce_store = InMemoryNonceStore()
    seen_at_agent: list[str] = []

    async def agent(request: Request) -> JSONResponse:  # noqa: ARG001
        seen_at_agent.append("hit")
        return JSONResponse({"result": "ok"})

    resource_server = MagicMock()
    resource_server.find_matching_requirements = MagicMock(return_value=REQUIREMENT)
    resource_server.verify_payment = AsyncMock(
        return_value=VerifyResponse(is_valid=True, invalid_reason=None, payer="0xBeef")
    )

    manifest = MagicMock()
    manifest.name = "test-agent"
    manifest.description = "test"
    manifest.did_extension = None

    from bindu.settings import app_settings

    original_methods = app_settings.x402.protected_methods
    app_settings.x402.protected_methods = ["message/send"]
    try:
        app = Starlette(
            routes=[Route("/", agent, methods=["POST"])],
            middleware=[
                Middleware(
                    X402Middleware,
                    manifest=manifest,
                    resource_server=resource_server,
                    x402_ext=MagicMock(),
                    payment_requirements=[REQUIREMENT],
                    nonce_store=nonce_store,
                )
            ],
        )
        client = TestClient(app)
        payload = make_payload(nonce="0x" + "ee" * 32)
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "message/send",
            "params": {"message": {"parts": [{"kind": "text", "text": "hi"}]}},
        }
        headers = {"X-PAYMENT": payment_header(payload)}

        first = client.post("/", json=body, headers=headers)
        second = client.post("/", json=body, headers=headers)
    finally:
        app_settings.x402.protected_methods = original_methods

    print(f"  First request:  HTTP {first.status_code}")
    print(f"  Second request: HTTP {second.status_code}")
    print(f"  Agent hits:     {len(seen_at_agent)} (only the first request reaches it)")
    if second.status_code == 402:
        body_json = second.json()
        print(f"  402 error:      {body_json.get('error')}")

    assert first.status_code == 200, "First request must reach the agent"
    assert second.status_code == 402, "Replay must be rejected with 402"
    assert len(seen_at_agent) == 1, "Agent must only see the first request"
    assert "replay" in second.json().get("error", "").lower()
