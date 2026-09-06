"""ManifestWorker implementation for executing tasks using AgentManifest.

Hybrid Agent Architecture (A2A Protocol):
    This worker implements a hybrid agent pattern where:

    1. Messages for Interaction (Task Open):
       - Agent responds with Messages during task execution
       - Task remains in 'working', 'input-required', or 'auth-required' state
       - No artifacts generated yet

    2. Artifacts for Completion (Task Terminal):
       - Agent responds with Artifacts when task completes
       - Task moves to 'completed' state (terminal)
       - Final deliverable is stored as artifact

    Example Flow:
        Context1
          └─ Task1 (state: working)
              ├─ Input1 → LLM → Output1 (Message, state: input-required)
              ├─ Input2 → LLM → Output2 (Message + Artifact, state: completed)

    A2A Protocol Compliance:
    - Tasks are immutable once terminal (completed/failed/canceled)
    - Refinements create NEW tasks with same contextId
    - referenceTaskIds link related tasks
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional
from uuid import UUID

from opentelemetry.trace import Status, StatusCode, get_current_span, get_tracer
from x402.http import FacilitatorConfig, HTTPFacilitatorClient

from bindu.settings import app_settings

from bindu.common.protocol.types import (
    Artifact,
    Message,
    Task,
    TaskIdParams,
    TaskSendParams,
    TaskState,
)
from bindu.penguin.manifest import AgentManifest
from bindu.server.workers.base import Worker
from bindu.server.workers.helpers import ResponseDetector, ResultProcessor
from bindu.utils.logging import get_logger
from bindu.utils.retry import retry_worker_operation
from bindu.utils.worker import ArtifactBuilder, MessageConverter, TaskStateManager

tracer = get_tracer("bindu.server.workers.manifest_worker")
logger = get_logger("bindu.server.workers.manifest_worker")

# Constants
TASK_NOT_FOUND_ERROR = "Task {task_id} not found"
INVALID_TERMINAL_STATE_ERROR = (
    "Invalid terminal state '{state}'. Must be one of: {terminal_states}"
)


@dataclass
class ManifestWorker(Worker):
    """Concrete worker implementation using AgentManifest for task execution.

    This worker wraps an AgentManifest and implements the hybrid agent pattern,
    handling state transitions, message generation, and artifact creation.

    Hybrid Pattern Implementation:
    - Detects agent response type (input-required, auth-required, or complete)
    - Returns Messages for interaction (task stays open)
    - Returns Artifacts for completion (task becomes immutable)

    Structured Response Support:
    - Parses JSON responses: {"state": "input-required", "prompt": "..."}
    - Falls back to heuristic detection for backward compatibility
    - Extracts metadata (auth_type, service) when available

    A2A Protocol Compliance:
    - Uses referenceTaskIds for conversation history
    - Maintains context continuity across tasks
    - Ensures task immutability after terminal states
    """

    manifest: AgentManifest
    """The agent manifest containing execution logic and DID identity."""

    lifecycle_notifier: Optional[Callable[[UUID, UUID, str, bool], Any]] = field(
        default=None
    )
    """Optional callback for task lifecycle notifications (task_id, context_id, state, final)."""

    @retry_worker_operation()
    async def run_task(self, params: TaskSendParams) -> None:
        """Execute a task using the AgentManifest.

        Hybrid Pattern Flow:
        1. Load task and validate state
        2. Build conversation history (using referenceTaskIds or context)
        3. Execute manifest with conversation context
        4. Detect response type:
           - input-required → Message only, task stays open
           - auth-required → Message only, task stays open
           - normal → Message + Artifact, task completes
        5. Update storage with appropriate state and content
        6. Settle payment if task completes successfully (x402 flow)

        Args:
            params: Task execution parameters containing task_id, context_id, message,
                   and optional payment_context from middleware

        Raises:
            ValueError: If task not found
            Exception: Re-raised after marking task as failed
        """
        # Step 1: Load and validate task
        task = await self.storage.load_task(params["task_id"])
        if task is None:
            raise ValueError(TASK_NOT_FOUND_ERROR.format(task_id=params["task_id"]))

        # Extract payment context if available (from x402 middleware)
        payment_context = params.get("payment_context")

        await TaskStateManager.validate_task_state(task)

        # Settle BEFORE doing any work (settle-first ordering).
        #
        # Rationale: x402 `/verify` is a probabilistic check, not a reservation —
        # the payer's balance can change between verify and settle, and parallel
        # nonces from the same wallet can pass verify independently. If we settle
        # only after the LLM call, every failed settle costs the agent the LLM
        # bill. Settling first means a failed settle has zero LLM cost.
        #
        # Google A2A's x402 extension takes the same approach for long-running
        # tasks; the latency is dominated by the LLM call anyway, so happy-path
        # wall-clock is unchanged.
        settlement_metadata: dict[str, Any] | None = None
        if payment_context:
            settlement_metadata = await self._settle_payment(payment_context)
            settled_ok = (
                settlement_metadata.get(app_settings.x402.meta_status_key)
                == app_settings.x402.status_completed
            )
            if not settled_ok:
                # No state transition to "working", no LLM call — just record
                # the failure and exit. Reconciliation metadata is already in
                # settlement_metadata (nonce, authorization, network).
                await self._handle_settlement_failure(task, settlement_metadata)
                return

        # Add span event for state transition
        self._add_state_change_event(to_state="working")

        # Transition to working
        await self.storage.update_task(task["id"], state="working")
        await self._notify_lifecycle(task["id"], task["context_id"], "working", False)

        # Step 2: Build conversation history (A2A Protocol)
        message_history = await self._build_complete_message_history(task)

        try:
            # Step 3: Execute manifest with system prompt (if enabled)
            if (
                self.manifest.enable_system_message
                and app_settings.agent.enable_structured_responses
            ):
                # Inject structured response system prompt as first message
                system_prompt = app_settings.agent.structured_response_system_prompt
                if system_prompt:
                    # Create new list to avoid mutating original message_history
                    message_history = [{"role": "system", "content": system_prompt}] + (
                        message_history or []
                    )

            # Step 3.1: Execute agent with tracing
            with tracer.start_as_current_span("agent.execute") as agent_span:
                start_time = time.time()

                # Set agent-specific attributes
                agent_span.set_attributes(
                    {
                        "bindu.agent.name": self.manifest.name,
                        "bindu.agent.did": str(self.manifest.did_extension.did),
                        "bindu.agent.message_count": len(message_history or []),
                        "bindu.component": "agent_execution",
                    }
                )

                try:
                    # Type narrowing: manifest.run should be callable
                    assert self.manifest.run is not None
                    # Pass message history as structured list of dicts
                    raw_results = self.manifest.run(message_history or [])

                    # Handle generator/async generator responses
                    collected_results = await ResultProcessor.collect_results(
                        raw_results
                    )

                    # Normalize result to extract final response (intelligent extraction)
                    results = ResultProcessor.normalize_result(collected_results)

                    # Record successful execution
                    execution_time = time.time() - start_time
                    agent_span.set_attribute(
                        "bindu.agent.execution_time", execution_time
                    )
                    agent_span.set_status(Status(StatusCode.OK))

                except Exception as agent_error:
                    # Record agent execution failure
                    execution_time = time.time() - start_time
                    agent_span.set_attributes(
                        {
                            "bindu.agent.execution_time": execution_time,
                            "bindu.agent.error_type": type(agent_error).__name__,
                            "bindu.agent.error_message": str(agent_error),
                        }
                    )
                    agent_span.set_status(Status(StatusCode.ERROR, str(agent_error)))
                    raise

            # Step 4: Parse response and detect state
            structured_response = ResponseDetector.parse_structured_response(results)

            # Determine task state based on response
            state, message_content = ResponseDetector.determine_task_state(
                results, structured_response
            )

            if state in ("input-required", "auth-required"):
                # Hybrid Pattern: Return Message only, keep task open
                # Add span event for state transition
                self._add_state_change_event(from_state="working", to_state=state)
                await self._handle_intermediate_state(task, state, message_content)
            else:
                # Hybrid Pattern: Task complete - generate Message + Artifacts
                # Add span event for state transition
                self._add_state_change_event(from_state="working", to_state=state)
                await self._handle_terminal_state(
                    task, results, state, settlement_metadata=settlement_metadata
                )

        except Exception as e:
            # Handle task failure with error message
            # Add span event for failure
            self._add_state_change_event(
                from_state="working", to_state="failed", error=str(e)
            )
            # If we already debited the payer (settle-first succeeded), the work
            # failure is an "orphan payment" — money moved, no artifact delivered.
            # x402 has no native refund; persist enough metadata for an operator
            # to issue a manual transfer back.
            await self._handle_task_failure(
                task, str(e), settlement_metadata=settlement_metadata
            )
            raise
        return

    @retry_worker_operation(max_attempts=2)
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a running task.

        Args:
            params: Task identification parameters containing task_id
        """
        task = await self.storage.load_task(params["task_id"])
        if task:
            # Add span event for cancellation
            self._add_state_change_event(
                from_state=task["status"]["state"], to_state="canceled"
            )
            await self.storage.update_task(params["task_id"], state="canceled")
            await self._notify_lifecycle(
                params["task_id"], task["context_id"], "canceled", True
            )

    def build_message_history(self, history: list[Message]) -> list[dict[str, Any]]:
        """Pass A2A protocol messages through verbatim — each keeps its ``parts``.

        Handlers read ``messages[-1]["parts"]`` (text / file / data parts)
        directly; that is the A2A contract agents are written against. Do NOT
        flatten to ``{role, content}`` here: it discards ``parts``, and the
        file interceptor cannot represent binary (PDF/image) bytes as text,
        so every file/vision handler receives an empty message. Chat-format
        flattening happens only at the gRPC boundary
        (``GrpcAgentClient._build_request``), whose proto requires it.

        Args:
            history: List of A2A protocol Message objects

        Returns:
            The same messages as plain dicts, ``parts`` intact.
        """
        return [{**m} for m in history]

    def build_artifacts(self, result: Any) -> list[Artifact]:
        """Convert manifest execution result to A2A protocol artifacts.

        Args:
            result: Agent execution result (any format)

        Returns:
            List of Artifact objects with DID signature

        Note:
            Only called when task completes (hybrid pattern)
        """
        did_extension = self.manifest.did_extension
        return ArtifactBuilder.from_result(result, did_extension=did_extension)

    async def _build_complete_message_history(self, task: Task) -> list[dict[str, Any]]:
        """Build complete conversation history following A2A Protocol.

        A2A Protocol Strategy:
        1. If referenceTaskIds present: Build from referenced tasks (explicit)
        2. Otherwise: Build from all tasks in context (implicit)

        This enables:
        - Task refinements with explicit references
        - Parallel task execution within same context
        - Conversation continuity across multiple tasks

        Args:
            task: Current task being executed

        Returns:
            List of A2A protocol messages (``parts`` intact) for agent execution
        """
        # Extract referenceTaskIds from current task message
        current_message = task.get("history", [])[0] if task.get("history") else None
        reference_task_ids: list = []

        if current_message and "reference_task_ids" in current_message:
            reference_task_ids = current_message["reference_task_ids"]

        if reference_task_ids:
            # Strategy 1: Explicit references (A2A refinement pattern)
            referenced_messages: list[Message] = []
            for task_id in reference_task_ids:
                # Ensure task_id is UUID object
                task_id_uuid = UUID(task_id) if isinstance(task_id, str) else task_id
                ref_task = await self.storage.load_task(task_id_uuid)
                if ref_task and ref_task.get("history"):
                    referenced_messages.extend(ref_task["history"])

            current_messages = task.get("history", [])
            all_messages = referenced_messages + current_messages

        elif self.manifest.enable_context_based_history:
            # Strategy 2: Context-based history (implicit continuation)
            # Only enabled if configured in manifest
            tasks_by_context = await self.storage.list_tasks_by_context(
                task["context_id"]
            )
            previous_tasks = [t for t in tasks_by_context if t["id"] != task["id"]]

            all_previous_messages: list[Message] = []
            for prev_task in previous_tasks:
                history = prev_task.get("history", [])
                if history:
                    all_previous_messages.extend(history)

            current_messages = task.get("history", [])
            all_messages = all_previous_messages + current_messages
        else:
            # No context-based history - only use current task messages
            all_messages = task.get("history", [])

        return self.build_message_history(all_messages) if all_messages else []

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _add_state_change_event(
        self,
        to_state: str,
        from_state: str | None = None,
        error: str | None = None,
    ) -> None:
        """Add state change event to current OpenTelemetry span.

        Args:
            to_state: Target state
            from_state: Optional source state
            error: Optional error message
        """
        current_span = get_current_span()
        if current_span.is_recording():
            attributes: dict[str, str] = {"to_state": to_state}
            if from_state:
                attributes["from_state"] = from_state
            if error:
                attributes["error"] = error
            current_span.add_event("task.state_changed", attributes=attributes)

    def _log_notification_error(
        self,
        notification_type: str,
        task_id: UUID,
        context_id: UUID,
        error: Exception,
        **extra_context: Any,
    ) -> None:
        """Log notification delivery errors.

        Args:
            notification_type: Type of notification (e.g., 'Lifecycle', 'Artifact')
            task_id: Task identifier
            context_id: Context identifier
            error: Exception that occurred
            **extra_context: Additional context to log
        """
        # ERROR + traceback rather than a one-line WARNING. A failed
        # notification is user-impacting (the operator's inbox never
        # receives the artifact or state transition) and silent
        # str(error) hides the call site — see the agno RunResponse →
        # DataPart serialization bug that vanished here for weeks.
        logger.opt(exception=error).error(
            f"{notification_type} notification failed",
            task_id=str(task_id),
            context_id=str(context_id),
            error=str(error),
            error_type=type(error).__name__,
            **extra_context,
        )

    # -------------------------------------------------------------------------
    # Message Normalization
    # -------------------------------------------------------------------------

    async def _handle_intermediate_state(
        self, task: Task, state: TaskState, message_content: Any
    ) -> None:
        """Handle intermediate task states (input-required, auth-required).

        A2A Protocol Compliance:
        - Agent messages are added to task.history
        - Task remains in mutable state (working, input-required, auth-required)
        - All information is in the message, no redundant metadata

        Args:
            task: Current task
            state: Task state to set
            message_content: Content for agent message (any type: str, dict, list, etc.)
        """
        # Render message content for user; for structured, prefer 'prompt' field
        content = (
            message_content.get("prompt")
            if isinstance(message_content, dict) and message_content.get("prompt")
            else message_content
        )
        agent_messages = MessageConverter.to_protocol_messages(
            content, task["id"], task["context_id"]
        )

        metadata: dict[str, Any] | None = None

        # Update task with state and append agent messages to history
        await self.storage.update_task(
            task["id"], state=state, new_messages=agent_messages, metadata=metadata
        )
        # Forward the rendered prompt to the operator inbox via the
        # lifecycle webhook. Coerce to a string conservatively — if the
        # handler returned a structured value without a "prompt" key,
        # `content` is still that raw value here.
        status_message = content if isinstance(content, str) else None
        await self._notify_lifecycle(
            task["id"], task["context_id"], state, False, status_message
        )

    async def _handle_terminal_state(
        self,
        task: Task,
        results: Any,
        state: TaskState = "completed",
        additional_metadata: dict[str, Any] | None = None,
        settlement_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Handle terminal task states (completed/failed).

        Hybrid Pattern - Terminal States:
        - completed: Message (explanation) + Artifacts (deliverable)
        - failed: Message (error explanation) only, NO artifacts
        - canceled: State change only, NO new content

        A2A Protocol Compliance:
        - Agent messages are added to task.history
        - Artifacts are added to task.artifacts (completed only)
        - Task becomes immutable after reaching terminal state

        X402 Payment Flow:
        - Settlement happens upfront in run_task (settle-first), so by the time
          we get here the payer has already been debited. We just attach the
          settlement metadata (receipts) to the task.

        Args:
            task: Task dict being finalized
            results: Agent execution results
            state: Terminal state (completed or failed)
            additional_metadata: Optional metadata to attach to task
            settlement_metadata: Pre-settled payment metadata from run_task

        Raises:
            ValueError: If state is not a terminal state
        """
        # Validate that state is terminal
        if state not in app_settings.agent.terminal_states:
            raise ValueError(
                INVALID_TERMINAL_STATE_ERROR.format(
                    state=state, terminal_states=app_settings.agent.terminal_states
                )
            )

        # Handle different terminal states
        if state == "completed":
            # Success: Add both Message and Artifacts
            agent_messages = MessageConverter.to_protocol_messages(
                results, task["id"], task["context_id"]
            )
            artifacts = self.build_artifacts(results)

            # Attach pre-settled payment metadata (receipts, tx hash) to the task.
            # Settlement itself happened upfront in run_task; if it had failed we
            # would not be in the "completed" branch.
            if settlement_metadata:
                if additional_metadata:
                    additional_metadata.update(settlement_metadata)
                else:
                    additional_metadata = settlement_metadata

            # Persist task state BEFORE sending any notifications (outbox pattern).
            # If a notification fires before the DB write and then the process crashes,
            # clients receive an artifact webhook but the task is still "working" in the
            # DB — an inconsistent state.  Write first, then notify.
            await self.storage.update_task(
                task["id"],
                state=state,
                new_artifacts=artifacts,
                new_messages=agent_messages,
                metadata=additional_metadata,
            )

            # Send artifact notifications after the DB is committed
            for artifact in artifacts:
                await self._notify_artifact(task["id"], task["context_id"], artifact)

            await self._notify_lifecycle(task["id"], task["context_id"], state, True)

        elif state in ("failed", "rejected"):
            # Failure/Rejection: Message only (explanation), NO artifacts
            error_message = MessageConverter.to_protocol_messages(
                results, task["id"], task["context_id"]
            )
            await self.storage.update_task(
                task["id"],
                state=state,
                new_messages=error_message,
                metadata=additional_metadata,
            )
            await self._notify_lifecycle(task["id"], task["context_id"], state, True)

        elif state == "canceled":
            # Canceled: State change only, NO new content
            await self.storage.update_task(task["id"], state=state)
            await self._notify_lifecycle(task["id"], task["context_id"], state, True)

    async def _handle_settlement_failure(
        self, task: Task, settlement_metadata: dict[str, Any]
    ) -> None:
        """Mark task failed because settle-first rejected the payment.

        Called from run_task BEFORE the task transitions to "working" — so
        no LLM call ran, no artifact was generated, nothing to withhold.
        ``settlement_metadata`` carries the recovery fields (nonce,
        authorization, network) for operator visibility.

        The user-facing message is intentionally generic — the facilitator's
        raw error string (which can disclose internal infra detail) stays in
        ``task.metadata[x402.payment.error]`` for the operator, not on the
        wire to the caller.
        """
        error_message = MessageConverter.to_protocol_messages(
            "Payment settlement failed; task not executed.",
            task["id"],
            task["context_id"],
        )
        self._add_state_change_event(
            from_state="submitted", to_state="failed", error="settlement_failed"
        )
        await self.storage.update_task(
            task["id"],
            state="failed",
            new_messages=error_message,
            metadata=settlement_metadata,
        )
        await self._notify_lifecycle(task["id"], task["context_id"], "failed", True)

    async def _handle_task_failure(
        self,
        task: Task,
        error: str,
        settlement_metadata: dict[str, Any] | None = None,
    ) -> None:
        """Handle task execution failure.

        Creates an error message and marks task as failed without artifacts.

        A2A Protocol Compliance:
        - Error message added to task.history
        - Task marked as failed (terminal state)

        X402 Orphan-Payment Handling:
        - Under settle-first, work failure happens AFTER the payer has been
          debited on-chain. We cannot auto-refund (x402 has no refund
          primitive), so we flag the payment as ``payment-orphaned`` and
          persist the EIP-3009 fields so an operator can issue a manual
          transfer back to the payer.

        Args:
            task: Task that failed
            error: Error description
            settlement_metadata: Pre-settled payment metadata, if present
        """
        error_message = MessageConverter.to_protocol_messages(
            f"Task execution failed: {error}", task["id"], task["context_id"]
        )
        metadata: dict[str, Any] | None = None
        if settlement_metadata:
            # Re-tag the status — the payment itself succeeded, but the work
            # didn't, so this is a refund-required state, not a settlement
            # failure. The receipts and EIP-3009 fields stay intact.
            metadata = {
                **settlement_metadata,
                app_settings.x402.meta_status_key: "payment-orphaned",
            }
        await self.storage.update_task(
            task["id"], state="failed", new_messages=error_message, metadata=metadata
        )
        await self._notify_lifecycle(task["id"], task["context_id"], "failed", True)

    async def _settle_payment(self, payment_context: dict[str, Any]) -> dict[str, Any]:
        """Settle payment after successful task completion.

        This method is called only when a task completes successfully with payment context.
        It calls the facilitator to settle the payment and returns metadata to attach to the task.

        Args:
            payment_context: Payment details from x402 middleware containing:
                - payment_payload: The payment payload from the client
                - payment_requirements: The payment requirements for this agent
                - verify_response: The verification response from facilitator

        Returns:
            Metadata dict containing settlement information to attach to task
        """
        # Pull the EIP-3009 fields out of the raw dict up front so they end
        # up in every failure return path. Validation or facilitator errors
        # otherwise strip the nonce/authorization, and we lose any chance to
        # reconcile a half-settled transaction later (issue #562).
        payment_payload_dict = payment_context.get("payment_payload", {}) or {}
        scheme_payload = payment_payload_dict.get("payload", {}) or {}
        authorization = scheme_payload.get("authorization", {}) or {}
        nonce = authorization.get("nonce")
        network = payment_payload_dict.get("network")

        def _failure_metadata(reason: str) -> dict[str, Any]:
            md: dict[str, Any] = {
                app_settings.x402.meta_status_key: app_settings.x402.status_failed,
                app_settings.x402.meta_error_key: reason,
            }
            if nonce is not None:
                md["x402_nonce"] = nonce
            if authorization:
                md["x402_authorization"] = authorization
            if network is not None:
                md["x402_network"] = network
            return md

        try:
            from x402 import PaymentPayload, PaymentRequirements

            payment_requirements_dict = payment_context["payment_requirements"]

            # Convert dicts back to Pydantic models (they were serialized in a2a_protocol)
            payment_payload = PaymentPayload.model_validate(payment_payload_dict)
            payment_requirements = PaymentRequirements.model_validate(
                payment_requirements_dict
            )

            # Initialize a fresh facilitator client per settlement. The
            # ResourceServer that holds a long-lived client for verify
            # lives on the application instance and is not in scope here.
            facilitator = HTTPFacilitatorClient(
                FacilitatorConfig(url=app_settings.x402.facilitator_url)
            )

            # Settle payment
            logger.info("Settling payment for completed task")
            settle_response = await facilitator.settle(
                payment_payload, payment_requirements
            )

            if settle_response.success:
                logger.info("Payment settled successfully")
                return {
                    app_settings.x402.meta_status_key: app_settings.x402.status_completed,
                    app_settings.x402.meta_receipts_key: [settle_response.model_dump()],
                }
            else:
                error_reason = settle_response.error_reason or "Unknown error"
                # loguru parses braces in the message template; values that may
                # contain JSON (`{...}`) — facilitator errors do — must go
                # through positional placeholders, not f-string interpolation.
                logger.error("Payment settlement failed: {}", error_reason)
                return _failure_metadata(error_reason)

        except Exception as e:
            # Same reason as above — exception strings from the x402 SDK
            # routinely embed the failing JSON body, which trips loguru's
            # template parser if we use an f-string here.
            logger.opt(exception=True).error("Error settling payment: {}", e)
            return _failure_metadata(str(e))

    async def _notify_artifact(
        self, task_id: UUID, context_id: UUID, artifact: Artifact
    ) -> None:
        """Notify about artifact generation if push manager is available.

        Args:
            task_id: Task identifier
            context_id: Context identifier
            artifact: The artifact that was generated
        """
        if self.lifecycle_notifier:
            try:
                # Get push manager from lifecycle_notifier's bound instance
                push_manager = getattr(self.lifecycle_notifier, "__self__", None)
                if push_manager and hasattr(push_manager, "notify_artifact"):
                    result = push_manager.notify_artifact(task_id, context_id, artifact)
                    if hasattr(result, "__await__"):
                        await result
            except Exception as e:
                # Log but don't disrupt task execution on notification errors
                self._log_notification_error("Artifact", task_id, context_id, e)

    async def _notify_lifecycle(
        self,
        task_id: UUID,
        context_id: UUID,
        state: str,
        final: bool,
        status_message: str | None = None,
    ) -> None:
        """Notify lifecycle changes if notifier is configured.

        Args:
            task_id: Task identifier
            context_id: Context identifier
            state: New task state
            final: Whether this is a terminal state
            status_message: Optional human-readable text for non-terminal
                states (e.g., the agent's prompt for input-required).
                Operator inboxes render this so the user can see what the
                agent is waiting on instead of just "state changed".
        """
        if self.lifecycle_notifier:
            try:
                # Pass status_message only when supported by the notifier's
                # signature — keeps third-party notifiers (which may still
                # have the 4-arg shape) working.
                try:
                    result = self.lifecycle_notifier(
                        task_id,
                        context_id,
                        state,
                        final,
                        status_message,  # ty: ignore[too-many-positional-arguments]
                    )
                except TypeError:
                    result = self.lifecycle_notifier(task_id, context_id, state, final)
                # Handle both sync and async notifiers
                if hasattr(result, "__await__"):
                    await result
            except Exception as e:
                # Log but don't disrupt task execution on notification errors
                self._log_notification_error(
                    "Lifecycle", task_id, context_id, e, state=state
                )
