from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from x402 import PaymentPayload, PaymentRequirements
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.workers.x402_reconciliation import reconcile_failed_payments
from bindu.settings import app_settings

REQUIREMENT = PaymentRequirements(
    scheme="exact",
    network="eip155:84532",
    asset="0x036cbd53842c5426634e7929541ec2318f3dcf7e",
    amount="1000000",  # 1 USDC (6 decimals)
    pay_to="0xa11ce000000000000000000000000000000a11ce",
    max_timeout_seconds=60,
    extra={"name": "USDC", "version": "2"},
)


def make_payload(nonce: str) -> PaymentPayload:
    """Build a syntactically valid EIP-3009 payload for the canonical requirement."""
    return PaymentPayload(
        x402_version=2,
        payload={
            "signature": "0x" + "00" * 65,
            "authorization": {
                "from": "0xb0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0b0",
                "to": REQUIREMENT.pay_to,
                "value": REQUIREMENT.amount,
                "validAfter": "0",
                "validBefore": "9999999999",
                "nonce": nonce,
            },
        },
        accepted=REQUIREMENT,
    )


@pytest.mark.asyncio
async def test_reconciliation_worker_success():
    """Verify that the reconciliation worker checks failed payments and marks successful ones as payment-orphaned."""
    storage = InMemoryStorage()
    task_id = uuid4()
    context_id = uuid4()
    nonce = "0x" + "ab" * 32

    payload = make_payload(nonce)
    payment_context = {
        "payment_payload": payload.model_dump(by_alias=True),
        "payment_requirements": REQUIREMENT.model_dump(by_alias=True),
        "verify_response": {"is_valid": True, "invalid_reason": None},
    }

    # Create initial message with payment context inside metadata
    message = {
        "task_id": task_id,
        "context_id": context_id,
        "message_id": uuid4(),
        "role": "user",
        "parts": [{"kind": "text", "text": "test task"}],
        "metadata": {
            "_payment_context": payment_context
        }
    }

    # Submit task to storage
    await storage.submit_task(context_id, message)  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]

    # Initial metadata when payment failed during first settle attempt
    metadata = {
        app_settings.x402.meta_status_key: "payment-failed",
        app_settings.x402.meta_error_key: "upstream timeout",
        "x402_nonce": nonce,
        "x402_network": "eip155:84532",
    }

    # Update task in storage to terminal failed state with failed payment metadata
    await storage.update_task(
        task_id,
        state="failed",
        metadata=metadata
    )

    # Patch the facilitator at the boundary _settle_payment uses.
    with patch("bindu.server.workers.x402_reconciliation.HTTPFacilitatorClient") as mock_fac_class:
        mock_fac = AsyncMock()
        response = MagicMock()
        response.success = True
        response.error_reason = None
        response.model_dump = MagicMock(return_value={"transaction": "0xreconciledtx"})
        mock_fac.settle = AsyncMock(return_value=response)
        mock_fac_class.return_value = mock_fac

        # Run the reconciliation step
        await reconcile_failed_payments(storage)

        # Assert task is updated in storage
        updated_task = await storage.load_task(task_id)
        assert updated_task is not None
        assert updated_task["status"]["state"] == "failed"

        meta = updated_task.get("metadata") or {}
        assert meta.get(app_settings.x402.meta_status_key) == "payment-orphaned"
        assert meta.get(app_settings.x402.meta_receipts_key) == [{"transaction": "0xreconciledtx"}]
        assert meta.get(app_settings.x402.meta_error_key) is None
