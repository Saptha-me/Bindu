"""End-to-end tests for the x402 v2 middleware.

These tests exercise the full ``dispatch`` path with a mocked
``x402ResourceServer`` so we cover the bug-fix invariants that the
v0.2.1 middleware regressed:

* Body-parse failure → 402 (never falls through to the agent).
* Missing X-PAYMENT → 402.
* Replayed payload (same nonce twice) → 402 on the second try.
* Facilitator says ``is_valid=False`` → 402 (no fall-through).
* Happy path → request reaches the agent with payment state attached.
"""

from __future__ import annotations

import base64
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from x402 import PaymentPayload, PaymentRequirements
from x402.schemas.responses import VerifyResponse

from bindu.server.middleware.x402.nonce_store import InMemoryNonceStore
from bindu.server.middleware.x402.x402_middleware import X402Middleware


REQUIREMENT = PaymentRequirements(
    scheme="exact",
    network="eip155:84532",
    asset="0x036cbd53842c5426634e7929541ec2318f3dcf7e",
    amount="1000",
    pay_to="0x0000000000000000000000000000000000000001",
    max_timeout_seconds=60,
    extra={"name": "USDC", "version": "2"},
)


def _payload(nonce: str = "0x" + "ab" * 32) -> PaymentPayload:
    return PaymentPayload(
        x402_version=2,
        payload={
            "signature": "0x" + "00" * 65,
            "authorization": {
                "from": "0x000000000000000000000000000000000000beef",
                "to": REQUIREMENT.pay_to,
                "value": REQUIREMENT.amount,
                "validAfter": "0",
                "validBefore": "9999999999",
                "nonce": nonce,
            },
        },
        accepted=REQUIREMENT,
    )


def _payment_header(payload: PaymentPayload) -> str:
    return base64.b64encode(payload.model_dump_json(by_alias=True).encode()).decode()


def _build_app(
    *,
    verify_result: VerifyResponse,
    nonce_store: InMemoryNonceStore | None = None,
    protected_methods: list[str] | None = None,
    state_recorder: dict[str, object] | None = None,
):
    """Spin up a minimal Starlette app with the middleware in front of
    an agent that simply echoes ``OK``."""

    async def agent(request: Request) -> JSONResponse:
        if state_recorder is not None:
            state_recorder["payment_payload"] = request.state.payment_payload
            state_recorder["payment_requirements"] = request.state.payment_requirements
            state_recorder["verify_response"] = request.state.verify_response
            state_recorder["payer"] = request.state.payer
        return JSONResponse({"ok": True})

    resource_server = MagicMock()
    resource_server.find_matching_requirements = MagicMock(return_value=REQUIREMENT)
    resource_server.verify_payment = AsyncMock(return_value=verify_result)

    manifest = MagicMock()
    manifest.name = "test-agent"
    manifest.description = "test"
    manifest.did_extension = None

    x402_ext = MagicMock()

    # Patch app_settings.x402.protected_methods just for the dispatch check.
    from bindu.settings import app_settings

    original = app_settings.x402.protected_methods
    app_settings.x402.protected_methods = protected_methods or ["message/send"]

    store = nonce_store or InMemoryNonceStore()

    routes = [Route("/", agent, methods=["POST"])]
    middleware = [
        Middleware(
            X402Middleware,
            manifest=manifest,
            resource_server=resource_server,
            x402_ext=x402_ext,
            payment_requirements=[REQUIREMENT],
            nonce_store=store,
        )
    ]
    app = Starlette(routes=routes, middleware=middleware)

    def restore():
        app_settings.x402.protected_methods = original

    return app, restore, resource_server, store


@pytest.fixture
def _restore_protected_methods():
    yield
    # safety net in case a test forgets to restore
    from bindu.settings import app_settings  # noqa: WPS433

    app_settings.x402.protected_methods = ["message/send"]


class TestBodyParseFailure:
    """``x402-middleware-fails-open-on-body-parse`` — was a bare
    ``except Exception`` that called ``call_next`` on parse failure.
    Must now return 402."""

    def test_malformed_json_returns_402(self, _restore_protected_methods):
        app, restore, *_ = _build_app(
            verify_result=VerifyResponse(is_valid=True, payer="0xbeef")
        )
        try:
            client = TestClient(app)
            r = client.post("/", content=b"\xff\xfe not valid json")
            assert r.status_code == 402
            assert "Malformed" in r.json()["error"]
        finally:
            restore()

    def test_invalid_utf8_returns_402(self, _restore_protected_methods):
        app, restore, *_ = _build_app(
            verify_result=VerifyResponse(is_valid=True, payer="0xbeef")
        )
        try:
            client = TestClient(app)
            r = client.post("/", content=b"\xc3\x28")  # invalid UTF-8 sequence
            assert r.status_code == 402
        finally:
            restore()


class TestMissingPaymentHeader:
    def test_missing_header_on_protected_method_returns_402(
        self, _restore_protected_methods
    ):
        app, restore, *_ = _build_app(
            verify_result=VerifyResponse(is_valid=True, payer="0xbeef")
        )
        try:
            client = TestClient(app)
            r = client.post("/", json={"jsonrpc": "2.0", "method": "message/send"})
            assert r.status_code == 402
            assert "X-PAYMENT" in r.json()["error"]
        finally:
            restore()

    def test_unprotected_method_skips_payment(self, _restore_protected_methods):
        app, restore, *_ = _build_app(
            verify_result=VerifyResponse(is_valid=True, payer="0xbeef"),
            protected_methods=["message/send"],
        )
        try:
            client = TestClient(app)
            r = client.post(
                "/",
                json={"jsonrpc": "2.0", "method": "tasks/get"},  # not protected
            )
            assert r.status_code == 200
        finally:
            restore()


class TestReplayPrevention:
    """``x402-no-replay-prevention`` — same nonce must not be accepted
    twice within validBefore. The nonce store enforces this before we
    pay for the facilitator round-trip."""

    def test_same_payload_replayed_is_rejected(self, _restore_protected_methods):
        store = InMemoryNonceStore()
        app, restore, server, _ = _build_app(
            verify_result=VerifyResponse(is_valid=True, payer="0xbeef"),
            nonce_store=store,
        )
        try:
            payload = _payload()
            header = _payment_header(payload)
            client = TestClient(app)

            body = {"jsonrpc": "2.0", "method": "message/send"}
            first = client.post("/", json=body, headers={"X-PAYMENT": header})
            assert first.status_code == 200

            second = client.post("/", json=body, headers={"X-PAYMENT": header})
            assert second.status_code == 402
            assert "replay" in second.json()["error"].lower()

            # The facilitator was only called once — the replay short-circuited
            # at the nonce check, before we paid for verification.
            assert server.verify_payment.await_count == 1
        finally:
            restore()

    def test_different_nonces_both_succeed(self, _restore_protected_methods):
        store = InMemoryNonceStore()
        app, restore, *_ = _build_app(
            verify_result=VerifyResponse(is_valid=True, payer="0xbeef"),
            nonce_store=store,
        )
        try:
            client = TestClient(app)
            body = {"jsonrpc": "2.0", "method": "message/send"}

            for nonce_byte in ("aa", "bb"):
                payload = _payload(nonce="0x" + nonce_byte * 32)
                r = client.post(
                    "/",
                    json=body,
                    headers={"X-PAYMENT": _payment_header(payload)},
                )
                assert r.status_code == 200, r.text
        finally:
            restore()


class TestFacilitatorRejection:
    """``x402-balance-check-skipped-on-missing-contract-code`` /
    ``x402-no-signature-verification`` — when the facilitator returns
    ``is_valid=False`` we must NOT fall through to the agent."""

    def test_invalid_payment_returns_402(self, _restore_protected_methods):
        app, restore, *_ = _build_app(
            verify_result=VerifyResponse(
                is_valid=False,
                invalid_reason="invalid_signature",
                payer="0xbeef",
            )
        )
        try:
            client = TestClient(app)
            r = client.post(
                "/",
                json={"jsonrpc": "2.0", "method": "message/send"},
                headers={"X-PAYMENT": _payment_header(_payload())},
            )
            assert r.status_code == 402
            assert "invalid_signature" in r.json()["error"]
        finally:
            restore()


class TestHappyPath:
    def test_valid_payment_reaches_agent(self, _restore_protected_methods):
        seen_state: dict[str, object] = {}
        app, restore, server, _ = _build_app(
            verify_result=VerifyResponse(is_valid=True, payer="0xbeef"),
            state_recorder=seen_state,
        )
        try:
            client = TestClient(app)
            payload = _payload()
            r = client.post(
                "/",
                json={"jsonrpc": "2.0", "method": "message/send"},
                headers={"X-PAYMENT": _payment_header(payload)},
            )
            assert r.status_code == 200
            assert r.json() == {"ok": True}
            server.verify_payment.assert_awaited_once()
            assert seen_state["payment_payload"] == payload
            assert seen_state["payment_requirements"] == REQUIREMENT
            verify_response = seen_state["verify_response"]
            assert getattr(verify_response, "is_valid") is True
            assert getattr(verify_response, "invalid_reason") is None
            assert seen_state["payer"] == "0xbeef"
        finally:
            restore()


class TestNoncelessPayload:
    def test_payload_without_nonce_is_rejected(self, _restore_protected_methods):
        app, restore, *_ = _build_app(
            verify_result=VerifyResponse(is_valid=True, payer="0xbeef")
        )
        try:
            payload = PaymentPayload(
                x402_version=2,
                payload={"signature": "0x00", "authorization": {"from": "0xbeef"}},
                accepted=REQUIREMENT,
            )
            client = TestClient(app)
            r = client.post(
                "/",
                json={"jsonrpc": "2.0", "method": "message/send"},
                headers={"X-PAYMENT": _payment_header(payload)},
            )
            assert r.status_code == 402
            assert "nonce" in r.json()["error"].lower()
        finally:
            restore()
