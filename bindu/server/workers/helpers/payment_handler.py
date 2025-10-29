"""Payment handling utilities for ManifestWorker.

This module handles x402 payment settlement and related operations.
"""

from __future__ import annotations

from typing import Any

from x402.facilitator import FacilitatorClient
from x402.types import PaymentPayload, PaymentRequirements

from bindu.common.protocol.types import TaskState
from bindu.extensions.x402.utils import (
    build_payment_completed_metadata,
    build_payment_failed_metadata,
)
from bindu.utils.logging import get_logger
from bindu.utils.worker_utils import MessageConverter

logger = get_logger("bindu.server.workers.helpers.payment_handler")


class PaymentHandler:
    """Handles x402 payment settlement and parsing.

    This class provides methods for:
    - Parsing payment payloads and requirements
    - Selecting matching payment requirements
    - Settling payments after successful execution

    Most methods are static for easy testing and reuse.
    """

    @staticmethod
    def parse_payment_payload(data: Any) -> PaymentPayload | None:
        """Parse payment payload from message metadata.

        Args:
            data: Payment payload data (dict or None)

        Returns:
            PaymentPayload object or None if parsing fails
        """
        if data is None:
            return None
        try:
            if hasattr(PaymentPayload, "model_validate"):
                return PaymentPayload.model_validate(data)  # type: ignore
            return PaymentPayload(**data)
        except Exception:
            return None

    @staticmethod
    def parse_payment_requirements(data: Any) -> PaymentRequirements | None:
        """Parse payment requirements from task metadata.

        Args:
            data: Payment requirements data (dict or None)

        Returns:
            PaymentRequirements object or None if parsing fails
        """
        if data is None:
            return None
        try:
            if hasattr(PaymentRequirements, "model_validate"):
                return PaymentRequirements.model_validate(data)  # type: ignore
            return PaymentRequirements(**data)
        except Exception:
            return None

    @staticmethod
    def select_requirement(
        required: Any, payload: PaymentPayload | None
    ) -> PaymentRequirements | None:
        """Select matching payment requirement from accepts array.

        Matches by scheme and network, or returns first requirement as fallback.

        Args:
            required: Payment requirements data with accepts array
            payload: Payment payload to match against

        Returns:
            Matching PaymentRequirements or None
        """
        if not required:
            return None
        accepts = required.get("accepts") if isinstance(required, dict) else None
        if not accepts:
            return None
        if payload is None:
            return PaymentHandler.parse_payment_requirements(accepts[0])

        # Match by scheme and network
        for req in accepts:
            if (
                isinstance(req, dict)
                and req.get("scheme") == getattr(payload, "scheme", None)
                and req.get("network") == getattr(payload, "network", None)
            ):
                return PaymentHandler.parse_payment_requirements(req)
        return PaymentHandler.parse_payment_requirements(accepts[0])

    @staticmethod
    async def settle_payment(
        task: dict[str, Any],
        results: Any,
        state: TaskState,
        payment_payload: PaymentPayload,
        payment_requirements: PaymentRequirements,
        storage: Any,
        terminal_state_handler: Any,
        lifecycle_notifier: Any = None,
    ) -> None:
        """Handle payment settlement after successful agent execution.

        Args:
            task: Task dict
            results: Agent execution results
            state: Task state (should be completed)
            payment_payload: Verified payment payload
            payment_requirements: Payment requirements
            storage: Storage instance for updating task
            terminal_state_handler: Callback to handle terminal state (from ManifestWorker)
            lifecycle_notifier: Optional lifecycle notification callback

        Note:
            If settlement succeeds, task completes with payment-completed metadata.
            If settlement fails, task returns to input-required state.

            This method handles both success and failure cases, updating the task
            appropriately and calling the terminal state handler or returning to
            input-required state.
        """
        try:
            facilitator_client = FacilitatorClient()
            settle_response = await facilitator_client.settle(
                payment_payload, payment_requirements
            )

            if settle_response.success:
                # Settlement succeeded - complete task with receipt
                md = build_payment_completed_metadata(
                    settle_response.model_dump(by_alias=True)
                    if hasattr(settle_response, "model_dump")
                    else dict(settle_response)
                )

                # Call terminal state handler with payment metadata
                await terminal_state_handler(task, results, state, md)
            else:
                # Settlement failed - return to input-required
                await PaymentHandler._handle_settlement_failure(
                    task,
                    settle_response.error_reason or "settlement_failed",
                    settle_response.model_dump(by_alias=True)
                    if hasattr(settle_response, "model_dump")
                    else dict(settle_response),
                    storage,
                    lifecycle_notifier,
                )

        except Exception as e:
            # Settlement exception - return to input-required
            await PaymentHandler._handle_settlement_failure(
                task,
                f"settlement_exception: {e}",
                None,
                storage,
                lifecycle_notifier,
            )

    @staticmethod
    async def _handle_settlement_failure(
        task: dict[str, Any],
        error_reason: str,
        receipt: dict | None,
        storage: Any,
        lifecycle_notifier: Any = None,
    ) -> None:
        """Handle settlement failure by returning task to input-required.

        Args:
            task: Task dict
            error_reason: Reason for settlement failure
            receipt: Optional settlement receipt/response
            storage: Storage instance
            lifecycle_notifier: Optional lifecycle notification callback
        """
        md = build_payment_failed_metadata(error_reason, receipt)
        error_message = f"Payment settlement failed: {error_reason}"
        err_msgs = MessageConverter.to_protocol_messages(
            error_message, task["id"], task["context_id"]
        )

        await storage.update_task(
            task["id"],
            state="input-required",
            new_messages=err_msgs,
            metadata=md,
        )

        # Notify lifecycle if notifier is configured
        if lifecycle_notifier:
            try:
                result = lifecycle_notifier(
                    task["id"], task["context_id"], "input-required", False
                )
                if hasattr(result, "__await__"):
                    await result
            except Exception as e:
                logger.warning(
                    "Lifecycle notification failed during settlement failure",
                    task_id=str(task["id"]),
                    error=str(e),
                )
