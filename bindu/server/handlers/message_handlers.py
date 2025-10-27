# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Saptha-me/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Message handlers for Bindu server.

This module handles message-related RPC requests including
sending messages and streaming responses.
"""

from __future__ import annotations

import inspect
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from bindu.common.protocol.types import (
    SendMessageRequest,
    SendMessageResponse,
    StreamMessageRequest,
    Task,
    TaskSendParams,
)
from bindu.utils.coinbase_utils import generate_coinbase_jwt

from ...utils.task_telemetry import trace_task_operation, track_active_task

if TYPE_CHECKING:
    from ..scheduler import Scheduler
    from ..storage import Storage


@dataclass
class MessageHandlers:
    """Handles message-related RPC requests."""

    scheduler: Scheduler
    storage: Storage[Any]
    manifest: Any | None = None
    workers: list[Any] | None = None
    context_id_parser: Any = None

    async def _handle_payment_required(
        self, context_id: Any, message: dict[str, Any], x402_ext: Any
    ) -> Task:
        """Handle payment-required response for agents with execution cost.

        Args:
            context_id: Context ID for the task
            message: User message
            x402_ext: X402AgentExtension instance

        Returns:
            Task with payment-required state and metadata
        """
        # Submit task to storage
        task: Task = await self.storage.submit_task(context_id, message)

        # Create payment requirements
        # Use DID as resource identifier for semantic agent identity
        payment_req = x402_ext.create_payment_requirements(
            resource=self.manifest.did_extension.did or self.manifest.id,
            description=f"Payment required to use {self.manifest.name}",
        )

        # Build payment-required metadata
        from bindu.extensions.x402.utils import build_payment_required_metadata

        payment_metadata = build_payment_required_metadata(
            {"x402Version": 1, "accepts": [payment_req.model_dump(by_alias=True)]}
        )

        # Create agent message explaining payment requirement
        from bindu.utils.worker_utils import MessageConverter

        agent_messages = MessageConverter.to_protocol_messages(
            f"Payment required: {x402_ext.amount_usd:.2f} USD ({x402_ext.token} on {x402_ext.network})",
            task["id"],
            context_id,
        )

        # Update task to input-required with payment metadata
        await self.storage.update_task(
            task["id"],
            state="input-required",
            new_messages=agent_messages,
            metadata=payment_metadata,
        )

        # Return updated task
        return await self.storage.load_task(task["id"])

    async def _handle_payment_verification(
        self, context_id: Any, message: dict[str, Any], task: Task
    ) -> Task | None:
        """Verify payment payload before allowing task execution.

        Args:
            context_id: Context ID for the task
            message: User message with payment payload
            task: Submitted task

        Returns:
            Task with payment-failed if verification fails, None if verification succeeds
        """
        from bindu.extensions.x402.utils import (
            build_payment_failed_metadata,
            build_payment_verified_metadata,
        )
        from bindu.settings import app_settings
        from bindu.utils.worker_utils import MessageConverter
        from x402.facilitator import FacilitatorClient
        from x402.types import PaymentPayload, PaymentRequirements

        message_metadata = message.get("metadata", {})
        payload_data = message_metadata.get(app_settings.x402.meta_payload_key)

        # Get payment requirements from task metadata
        task_metadata = task.get("metadata", {})
        required_data = task_metadata.get(app_settings.x402.meta_required_key)

        if not required_data:
            # No payment requirements found - this shouldn't happen
            error_msg = MessageConverter.to_protocol_messages(
                "Payment requirements not found", task["id"], context_id
            )
            await self.storage.update_task(
                task["id"],
                state="input-required",
                new_messages=error_msg,
                metadata=build_payment_failed_metadata("missing_requirements"),
            )
            return await self.storage.load_task(task["id"])

        try:
            # Parse payment payload
            payment_payload = PaymentPayload(**payload_data)

            # Select matching requirement
            accepts = required_data.get("accepts", [])
            if not accepts:
                raise ValueError("No payment requirements in accepts array")

            # Match by scheme and network, or use first
            payment_requirement = None
            for req in accepts:
                if (
                    req.get("scheme") == payment_payload.scheme
                    and req.get("network") == payment_payload.network
                ):
                    if hasattr(PaymentRequirements, "model_validate"):
                        payment_requirement = PaymentRequirements.model_validate(req)
                    else:
                        payment_requirement = PaymentRequirements(**req)
                    break

            if not payment_requirement:
                # Use first requirement as fallback
                if hasattr(PaymentRequirements, "model_validate"):
                    payment_requirement = PaymentRequirements.model_validate(accepts[0])
                else:
                    payment_requirement = PaymentRequirements(**accepts[0])

            # Verify payment with facilitator
            facilitator = FacilitatorClient()
            try:
                jwt_token = generate_coinbase_jwt(
                    request_method=self.manifest.coinbase_config.request_method,
                    request_host=self.manifest.coinbase_config.request_host,
                    request_path=self.manifest.coinbase_config.request_path,
                )
                verify_response = await facilitator.verify(
                    payment_payload, payment_requirement, jwt_token
                )
            except Exception as e:
                print(f"DEBUG facilitator.verify() exception: {e}")
                print(f"DEBUG exception type: {type(e)}")
                raise

            print(f"DEBUG verify_response: {verify_response}")
            print(f"DEBUG verify_response.is_valid: {verify_response.is_valid}")
            if hasattr(verify_response, 'invalid_reason'):
                print(f"DEBUG verify_response.invalid_reason: {verify_response.invalid_reason}")

            if not verify_response.is_valid:
                # Verification failed
                error_msg = MessageConverter.to_protocol_messages(
                    f"Payment verification failed: {verify_response.invalid_reason or 'unknown'}",
                    task["id"],
                    context_id,
                )
                await self.storage.update_task(
                    task["id"],
                    state="input-required",
                    new_messages=error_msg,
                    metadata=build_payment_failed_metadata(
                        verify_response.invalid_reason or "verification_failed"
                    ),
                )
                return await self.storage.load_task(task["id"])

            # Verification succeeded - mark as verified and allow execution
            await self.storage.update_task(
                task["id"],
                metadata=build_payment_verified_metadata(),
            )
            return None  # None means verification passed, proceed with execution

        except Exception as e:
            # Payment processing error
            error_msg = MessageConverter.to_protocol_messages(
                f"Payment processing error: {str(e)}", task["id"], context_id
            )
            await self.storage.update_task(
                task["id"],
                state="input-required",
                new_messages=error_msg,
                metadata=build_payment_failed_metadata(f"processing_error: {str(e)}"),
            )
            return await self.storage.load_task(task["id"])

    @trace_task_operation("send_message")
    @track_active_task
    async def send_message(self, request: SendMessageRequest) -> SendMessageResponse:
        """Send a message using the A2A protocol."""
        message = request["params"]["message"]
        context_id = self.context_id_parser(message.get("context_id"))

        # Check if agent requires payment and no payment provided
        message_metadata = message.get("metadata", {})
        has_payment_payload = message_metadata.get("x402.payment.payload") is not None

        if not has_payment_payload and self.manifest:
            # Check if agent has x402 extension in capabilities
            from bindu.utils import get_x402_extension_from_capabilities

            x402_ext = get_x402_extension_from_capabilities(self.manifest)
            if x402_ext:
                # Agent requires payment - return payment-required immediately
                task = await self._handle_payment_required(
                    context_id, message, x402_ext
                )
                return SendMessageResponse(jsonrpc="2.0", id=request["id"], result=task)

        # Submit task to storage
        task: Task = await self.storage.submit_task(context_id, message)

        # If payment payload is present, verify it BEFORE scheduling
        if has_payment_payload:
            from bindu.settings import app_settings

            payment_status = message_metadata.get(app_settings.x402.meta_status_key)
            if payment_status == app_settings.x402.status_submitted:
                # Verify payment
                failed_task = await self._handle_payment_verification(
                    context_id, message, task
                )
                if failed_task:
                    # Verification failed - return task with error
                    return SendMessageResponse(
                        jsonrpc="2.0", id=request["id"], result=failed_task
                    )
                # Verification passed - continue to schedule task

        # Schedule task for execution
        scheduler_params: TaskSendParams = TaskSendParams(
            task_id=task["id"],
            context_id=context_id,
            message=message,
        )

        # Add optional configuration parameters
        config = request["params"].get("configuration", {})
        if history_length := config.get("history_length"):
            scheduler_params["history_length"] = history_length

        await self.scheduler.run_task(scheduler_params)
        return SendMessageResponse(jsonrpc="2.0", id=request["id"], result=task)

    async def stream_message(self, request: StreamMessageRequest):
        """Stream messages using Server-Sent Events.

        This method returns a StreamingResponse directly to support SSE,
        which will be handled at the application layer.
        """
        from starlette.responses import StreamingResponse

        message = request["params"]["message"]
        context_id = self.context_id_parser(message.get("context_id"))

        # similar to the "messages/send flow submit the task to the configured storage"
        task: Task = await self.storage.submit_task(context_id, message)

        async def stream_generator():
            """Generate a consumable stream based on the function which was decorated using pebblify."""
            try:
                await self.storage.update_task(task["id"], state="working")
                # yield the initial status update event to indicate processing of the task has started
                status_event = {
                    "kind": "status-update",
                    "task_id": str(task["id"]),
                    "context_id": str(context_id),
                    "status": {
                        "state": "working",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "final": False,
                }
                yield f"data: {json.dumps(status_event)}\n\n"

                if self.workers and self.manifest:
                    worker = self.workers[0]
                    message_history = await worker._build_complete_message_history(task)
                    manifest_result = self.manifest.run(message_history)

                    if inspect.isasyncgen(manifest_result):
                        async for chunk in manifest_result:
                            if chunk:
                                artifact_event = {
                                    "kind": "artifact-update",
                                    "task_id": str(task["id"]),
                                    "context_id": str(context_id),
                                    "artifact": {
                                        "artifact_id": str(uuid.uuid4()),
                                        "name": "streaming_response",
                                        "parts": [{"kind": "text", "text": str(chunk)}],
                                    },
                                    "append": True,
                                    "last_chunk": False,
                                }
                                yield f"data: {json.dumps(artifact_event)}\n\n"

                    elif inspect.isgenerator(manifest_result):
                        for chunk in manifest_result:
                            if chunk:
                                artifact_event = {
                                    "kind": "artifact-update",
                                    "task_id": str(task["id"]),
                                    "context_id": str(context_id),
                                    "artifact": {
                                        "artifact_id": str(uuid.uuid4()),
                                        "name": "streaming_response",
                                        "parts": [{"kind": "text", "text": str(chunk)}],
                                    },
                                    "append": True,
                                    "last_chunk": False,
                                }
                                yield f"data: {json.dumps(artifact_event)}\n\n"

                    else:
                        if manifest_result:
                            artifact_event = {
                                "kind": "artifact-update",
                                "task_id": str(task["id"]),
                                "context_id": str(context_id),
                                "artifact": {
                                    "artifact_id": str(uuid.uuid4()),
                                    "name": "response",
                                    "parts": [
                                        {"kind": "text", "text": str(manifest_result)}
                                    ],
                                },
                                "last_chunk": True,
                            }
                            yield f"data: {json.dumps(artifact_event)}\n\n"

                # Send completion status
                completion_event = {
                    "kind": "status-update",
                    "task_id": str(task["id"]),
                    "context_id": str(context_id),
                    "status": {
                        "state": "completed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "final": True,
                }
                yield f"data: {json.dumps(completion_event)}\n\n"

                # Update task state in storage
                await self.storage.update_task(task["id"], state="completed")
            except Exception as e:
                error_event = {
                    "kind": "status-update",
                    "task_id": str(task["id"]),
                    "context_id": str(context_id),
                    "status": {
                        "state": "failed",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                    "final": True,
                    "error": str(e),
                }
                yield f"data: {json.dumps(error_event)}\n\n"
                await self.storage.update_task(task["id"], state="failed")

        return StreamingResponse(stream_generator(), media_type="text/event-stream")
