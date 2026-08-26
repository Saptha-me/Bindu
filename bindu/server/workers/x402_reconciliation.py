"""Background worker for reconciling failed x402 payment settlements.

Queries the facilitator periodically to verify if transaction nonces
for failed tasks have been settled on-chain (reconciling transient timeouts).
"""

from __future__ import annotations

import asyncio
from typing import Any

from x402 import PaymentPayload, PaymentRequirements
from x402.http import FacilitatorConfig, HTTPFacilitatorClient

from bindu.settings import app_settings
from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.workers.x402_reconciliation")


async def run_x402_reconciliation_loop(storage: Any, interval_seconds: float = 30.0) -> None:
    """Run the background periodic loop for x402 payment reconciliation."""
    logger.info("Starting x402 payment reconciliation background loop")
    while True:
        try:
            await asyncio.sleep(interval_seconds)
            await reconcile_failed_payments(storage)
        except asyncio.CancelledError:
            logger.info("x402 payment reconciliation loop cancelled")
            break
        except Exception as e:
            logger.exception("Error in x402 payment reconciliation loop: %s", e)


async def reconcile_failed_payments(storage: Any) -> None:
    """Scan recent tasks for failed settlements and check if they confirmed on-chain."""
    try:
        # Check most recent 100 tasks in the database
        tasks = await storage.list_tasks(length=100)
    except Exception as e:
        logger.warning("Failed to list tasks for x402 reconciliation: %s", e)
        return

    for task in tasks:
        # We only reconcile tasks that are in a terminal 'failed' state
        if task.get("status", {}).get("state") != "failed":
            continue

        metadata = task.get("metadata") or {}
        payment_status = metadata.get(app_settings.x402.meta_status_key)

        # Only process tasks whose payment status is specifically 'payment-failed'
        if payment_status != app_settings.x402.status_failed:
            continue

        # Extract payment context from the initial message metadata to get the original payload
        history = task.get("history") or []
        if not history:
            continue

        first_msg = history[0]
        msg_metadata = first_msg.get("metadata") or {}
        payment_context = msg_metadata.get("_payment_context")
        if not payment_context:
            continue

        payment_payload_dict = payment_context.get("payment_payload")
        payment_requirements_dict = payment_context.get("payment_requirements")

        if not payment_payload_dict or not payment_requirements_dict:
            continue

        logger.info("Reconciling payment status for task: %s", task["id"])

        try:
            # Reconstitute the Pydantic models from the stored payment context
            payment_payload = PaymentPayload.model_validate(payment_payload_dict)
            payment_requirements = PaymentRequirements.model_validate(
                payment_requirements_dict
            )

            # Build a facilitator client
            facilitator = HTTPFacilitatorClient(
                FacilitatorConfig(url=app_settings.x402.facilitator_url)
            )

            # Re-attempt settle (this is idempotent on the facilitator/node side)
            settle_response = await facilitator.settle(
                payment_payload, payment_requirements
            )

            if settle_response.success:
                logger.info(
                    "Reconciliation succeeded: payment for task %s confirmed on-chain. "
                    "Updating payment status to payment-orphaned.",
                    task["id"],
                )
                # Flip payment status to 'payment-orphaned' because payment went through
                # but the task remained unexecuted (failed during initial worker state).
                updated_metadata = {
                    **metadata,
                    app_settings.x402.meta_status_key: "payment-orphaned",
                    app_settings.x402.meta_receipts_key: [settle_response.model_dump()],
                }
                # Clear error reasons as we resolved this payment
                updated_metadata[app_settings.x402.meta_error_key] = None

                await storage.update_task(
                    task["id"],
                    state="failed",
                    metadata=updated_metadata,
                )
            else:
                logger.debug(
                    "Reconciliation check for task %s completed. On-chain settlement not confirmed: %s",
                    task["id"],
                    settle_response.error_reason,
                )

        except Exception as e:
            # Catch transient facilitator network/timeout errors so we try again next tick
            logger.debug(
                "Facilitator error during reconciliation check for task %s: %s",
                task["id"],
                e,
            )
