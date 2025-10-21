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

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional
from uuid import UUID

from opentelemetry.trace import Status, StatusCode, get_tracer

# x402
from x402.types import PaymentPayload, PaymentRequirements
from x402.facilitator import FacilitatorClient
from bindu.extensions.x402.utils import (
    build_payment_completed_metadata,
    build_payment_failed_metadata,
    build_payment_required_metadata,
    build_payment_verified_metadata,
)
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
from bindu.utils.logging import get_logger
from bindu.utils.worker_utils import ArtifactBuilder, MessageConverter, TaskStateManager

tracer = get_tracer("bindu.server.workers.manifest_worker")
logger = get_logger("bindu.server.workers.manifest_worker")


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

    # -------------------------------------------------------------------------
    # Task Execution (Hybrid Pattern)
    # -------------------------------------------------------------------------

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

        Args:
            params: Task execution parameters containing task_id, context_id, message

        Raises:
            ValueError: If task not found
            Exception: Re-raised after marking task as failed
        """
        # Step 1: Load and validate task
        task = await self.storage.load_task(params["task_id"])
        if task is None:
            raise ValueError(f"Task {params['task_id']} not found")

        await TaskStateManager.validate_task_state(task)

        # Add span event for state transition
        from opentelemetry.trace import get_current_span

        current_span = get_current_span()
        if current_span.is_recording():
            current_span.add_event(
                "task.state_changed", attributes={"to_state": "working"}
            )

        # Detect x402 payment submission on the latest user message BEFORE setting state
        latest_msg = (task.get("history") or [])[-1] if task.get("history") else None
        latest_meta = (latest_msg or {}).get("metadata") or {}

        is_paid_flow = False
        payment_payload_obj: PaymentPayload | None = None
        payment_requirements_obj: PaymentRequirements | None = None
        facilitator_client: FacilitatorClient | None = None

        try:
            if latest_meta.get(
                app_settings.x402.meta_status_key
            ) == app_settings.x402.status_submitted and latest_meta.get(
                app_settings.x402.meta_payload_key
            ):
                payload_data = latest_meta.get(app_settings.x402.meta_payload_key)
                required_data = (task.get("metadata") or {}).get(
                    app_settings.x402.meta_required_key
                ) or latest_meta.get(app_settings.x402.meta_required_key)

                # Parse payload and select requirement
                payment_payload_obj = self._parse_payment_payload(payload_data)
                payment_requirements_obj = self._select_requirement_from_required(
                    required_data, payment_payload_obj
                )
                if payment_payload_obj and payment_requirements_obj:
                    facilitator_client = FacilitatorClient()
                    verify_response = await facilitator_client.verify(
                        payment_payload_obj, payment_requirements_obj
                    )
                    if not verify_response.is_valid:
                        # Record failure and finish task
                        md = build_payment_failed_metadata(
                            verify_response.invalid_reason or "verification_failed"
                        )
                        error_msg = MessageConverter.to_protocol_messages(
                            f"Payment verification failed: {verify_response.invalid_reason or 'unknown'}",
                            task["id"],
                            task["context_id"],
                        )
                        # Keep state as input-required per design; only metadata reflects x402 failure
                        await self.storage.update_task(
                            task["id"],
                            state="input-required",
                            new_messages=error_msg,
                            metadata=md,
                        )
                        await self._notify_lifecycle(
                            task["id"], task["context_id"], "input-required", False
                        )
                        return

                    # Mark verified while continuing work
                    is_paid_flow = True
                    await self.storage.update_task(
                        task["id"],
                        state="input-required",
                        metadata=build_payment_verified_metadata(),
                    )
        except Exception as e:
            # Defensive: if verification path errors, fail the task
            error_msg = MessageConverter.to_protocol_messages(
                f"Payment processing error: {e}", task["id"], task["context_id"]
            )
            await self.storage.update_task(
                task["id"], state="input-required", new_messages=error_msg
            )
            await self._notify_lifecycle(
                task["id"], task["context_id"], "input-required", False
            )
            return

        # If not in payment-submitted flow, transition to working as usual
        if not is_paid_flow:
            await self.storage.update_task(task["id"], state="working")
            await self._notify_lifecycle(
                task["id"], task["context_id"], "working", False
            )

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
                    # Pass message history as structured list of dicts
                    raw_results = self.manifest.run(message_history or [])

                    # Handle generator/async generator responses
                    collected_results = await self._collect_results(raw_results)

                    # Normalize result to extract final response (intelligent extraction)
                    results = self._normalize_result(collected_results)

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
            structured_response = self._parse_structured_response(results)

            # Determine task state based on response
            state, message_content = self._determine_task_state(
                results, structured_response
            )

            if state in ("input-required", "auth-required"):
                # Hybrid Pattern: Return Message only, keep task open
                # Add span event for state transition
                current_span = get_current_span()
                if current_span.is_recording():
                    current_span.add_event(
                        "task.state_changed",
                        attributes={"from_state": "working", "to_state": state},
                    )
                await self._handle_intermediate_state(task, state, message_content)
            else:
                # Hybrid Pattern: Task complete - generate Message + Artifacts
                # Add span event for state transition
                current_span = get_current_span()
                if current_span.is_recording():
                    current_span.add_event(
                        "task.state_changed",
                        attributes={"from_state": "working", "to_state": state},
                    )
                if (
                    is_paid_flow
                    and payment_payload_obj
                    and payment_requirements_obj
                    and facilitator_client
                ):
                    # Settle before final update so metadata includes receipt
                    try:
                        settle_response = await facilitator_client.settle(
                            payment_payload_obj, payment_requirements_obj
                        )
                        if settle_response.success:
                            md = build_payment_completed_metadata(
                                settle_response.model_dump(by_alias=True)
                                if hasattr(settle_response, "model_dump")
                                else dict(settle_response)
                            )
                            await self._handle_terminal_state(
                                task, results, state, additional_metadata=md
                            )
                        else:
                            md = build_payment_failed_metadata(
                                settle_response.error_reason or "settlement_failed",
                                (
                                    settle_response.model_dump(by_alias=True)
                                    if hasattr(settle_response, "model_dump")
                                    else dict(settle_response)
                                ),
                            )
                            # Keep task open (input-required) and attach failure metadata & message
                            error_message = f"Payment settlement failed: {settle_response.error_reason or 'unknown'}"
                            err_msgs = MessageConverter.to_protocol_messages(
                                error_message, task["id"], task["context_id"]
                            )
                            await self.storage.update_task(
                                task["id"],
                                state="input-required",
                                new_messages=err_msgs,
                                metadata=md,
                            )
                            await self._notify_lifecycle(
                                task["id"], task["context_id"], "input-required", False
                            )
                            return
                    except Exception as e:
                        md = build_payment_failed_metadata(f"settlement_exception: {e}")
                        err_msgs = MessageConverter.to_protocol_messages(
                            str(e), task["id"], task["context_id"]
                        )
                        await self.storage.update_task(
                            task["id"],
                            state="input-required",
                            new_messages=err_msgs,
                            metadata=md,
                        )
                        await self._notify_lifecycle(
                            task["id"], task["context_id"], "input-required", False
                        )
                        return
                else:
                    await self._handle_terminal_state(task, results, state)

        except Exception as e:
            # Handle task failure with error message
            # Add span event for failure
            current_span = get_current_span()
            if current_span.is_recording():
                current_span.add_event(
                    "task.state_changed",
                    attributes={
                        "from_state": "working",
                        "to_state": "failed",
                        "error": str(e),
                    },
                )
            await self._handle_task_failure(task, str(e))
            raise

    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a running task.

        Args:
            params: Task identification parameters containing task_id
        """
        task = await self.storage.load_task(params["task_id"])
        if task:
            # Add span event for cancellation
            from opentelemetry.trace import get_current_span

            current_span = get_current_span()
            if current_span.is_recording():
                current_span.add_event(
                    "task.state_changed",
                    attributes={
                        "from_state": task["status"]["state"],
                        "to_state": "canceled",
                    },
                )
            await self.storage.update_task(params["task_id"], state="canceled")
            await self._notify_lifecycle(
                params["task_id"], task["context_id"], "canceled", True
            )

    # -------------------------------------------------------------------------
    # Protocol Conversion
    # -------------------------------------------------------------------------

    def build_message_history(self, history: list[Message]) -> list[dict[str, str]]:
        """Convert A2A protocol messages to chat format for manifest execution.

        Args:
            history: List of A2A protocol Message objects

        Returns:
            List of dicts with 'role' and 'content' keys for LLM consumption
        """
        return MessageConverter.to_chat_format(history)

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

    # -------------------------------------------------------------------------
    # A2A Protocol - Conversation History
    # -------------------------------------------------------------------------

    async def _build_complete_message_history(self, task: Task) -> list[dict[str, str]]:
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
            List of chat-formatted messages for agent execution
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
                ref_task = await self.storage.load_task(task_id)
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
    # Message Normalization
    # -------------------------------------------------------------------------

    async def _handle_intermediate_state(
        self, task: dict[str, Any], state: TaskState, message_content: Any
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
        # If this is an x402 payment-required structured object, attach metadata
        if isinstance(message_content, dict):
            st = message_content.get("state")
            if st == app_settings.x402.status_required or "required" in message_content:
                required = message_content.get("required") or message_content
                metadata = build_payment_required_metadata(required)

        # Update task with state and append agent messages to history
        await self.storage.update_task(
            task["id"], state=state, new_messages=agent_messages, metadata=metadata
        )
        await self._notify_lifecycle(task["id"], task["context_id"], state, False)

    # -------------------------------------------------------------------------
    # Terminal State Handling
    # -------------------------------------------------------------------------

    async def _handle_terminal_state(
        self,
        task: dict[str, Any],
        results: Any,
        state: TaskState = "completed",
        additional_metadata: dict[str, Any] | None = None,
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

        Args:
            task: Task dict being finalized
            results: Agent execution results
            state: Terminal state (completed or failed)

        Raises:
            ValueError: If state is not a terminal state
        """
        # Validate that state is terminal
        if state not in app_settings.agent.terminal_states:
            raise ValueError(
                f"Invalid terminal state '{state}'. Must be one of: {app_settings.agent.terminal_states}"
            )

        # Handle different terminal states
        if state == "completed":
            # Success: Add both Message and Artifacts
            agent_messages = MessageConverter.to_protocol_messages(
                results, task["id"], task["context_id"]
            )
            artifacts = self.build_artifacts(results)

            await self.storage.update_task(
                task["id"],
                state=state,
                new_artifacts=artifacts,
                new_messages=agent_messages,
                metadata=additional_metadata,
            )
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

    async def _handle_task_failure(self, task: dict[str, Any], error: str) -> None:
        """Handle task execution failure.

        Creates an error message and marks task as failed without artifacts.

        A2A Protocol Compliance:
        - Error message added to task.history
        - Task marked as failed (terminal state)

        Args:
            task: Task that failed
            error: Error description
        """
        error_message = MessageConverter.to_protocol_messages(
            f"Task execution failed: {error}", task["id"], task["context_id"]
        )
        await self.storage.update_task(
            task["id"], state="failed", new_messages=error_message
        )
        await self._notify_lifecycle(task["id"], task["context_id"], "failed", True)

    # -------------------------------------------------------------------------
    # x402 helpers
    # -------------------------------------------------------------------------

    def _parse_payment_payload(self, data: Any) -> PaymentPayload | None:
        if data is None:
            return None
        try:
            if hasattr(PaymentPayload, "model_validate"):
                return PaymentPayload.model_validate(data)  # type: ignore
            return PaymentPayload(**data)
        except Exception:
            return None

    def _parse_payment_requirements(self, data: Any) -> PaymentRequirements | None:
        if data is None:
            return None
        try:
            if hasattr(PaymentRequirements, "model_validate"):
                return PaymentRequirements.model_validate(data)  # type: ignore
            return PaymentRequirements(**data)
        except Exception:
            return None

    def _select_requirement_from_required(
        self, required: Any, payload: PaymentPayload | None
    ) -> PaymentRequirements | None:
        if not required:
            return None
        accepts = required.get("accepts") if isinstance(required, dict) else None
        if not accepts:
            return None
        if payload is None:
            return self._parse_payment_requirements(accepts[0])
        # Match by scheme and network
        for req in accepts:
            if (
                isinstance(req, dict)
                and req.get("scheme") == getattr(payload, "scheme", None)
                and req.get("network") == getattr(payload, "network", None)
            ):
                return self._parse_payment_requirements(req)
        return self._parse_payment_requirements(accepts[0])

    # -------------------------------------------------------------------------
    # Result Collection
    # -------------------------------------------------------------------------

    async def _collect_results(self, raw_results: Any) -> Any:
        """Collect results from manifest execution.

        Handles different result types:
        - Direct return: str, dict, list, etc.
        - Generator: Collect all yielded values
        - Async generator: Await and collect all yielded values

        Args:
            raw_results: Raw result from manifest.run()

        Returns:
            Collected result (single value or last yielded value)
        """
        # Check if it's an async generator
        if hasattr(raw_results, "__anext__"):
            collected = []
            try:
                async for chunk in raw_results:
                    collected.append(chunk)
            except StopAsyncIteration:
                pass
            # Return last chunk or all chunks if multiple
            return collected[-1] if collected else None

        # Check if it's a sync generator
        elif hasattr(raw_results, "__next__"):
            collected = []
            try:
                for chunk in raw_results:
                    collected.append(chunk)
            except StopIteration:
                pass
            # Return last chunk or all chunks if multiple
            return collected[-1] if collected else None

        # Direct return value (str, dict, list, etc.)
        else:
            return raw_results

    def _normalize_result(self, result: Any) -> Any:
        """Intelligently normalize agent result to extract final response.

        This method gives users full control over what they return from handlers:
        - Return raw agent output → System extracts intelligently
        - Return pre-extracted string → System uses directly
        - Return structured dict → System respects state transitions

        Handles multiple formats from different frameworks:
        - Plain string: "Hello!" → "Hello!"
        - Dict with state: {"state": "input-required", ...} → pass through
        - Dict with content: {"content": "Hello!"} → "Hello!"
        - List of messages: [Message(...), Message(content="Hello!")] → "Hello!"
        - Message object: Message(content="Hello!") → "Hello!"
        - Custom objects: Try .content, .to_dict()["content"], or str()

        Args:
            result: Raw result from handler function

        Returns:
            Normalized result (str, dict with state, or original if can't normalize)
        """
        # Strategy 1: Already a string - use directly
        if isinstance(result, str):
            return result

        # Strategy 2: Dict with "state" key - structured response (pass through)
        if isinstance(result, dict):
            if "state" in result:
                return result  # Structured state transition
            elif "content" in result:
                return result["content"]  # Extract content from dict
            else:
                return result  # Unknown dict format, pass through

        # Strategy 3: List (e.g., list of Message objects from Agno)
        if isinstance(result, list) and result:
            last_item = result[-1]

            # Try to extract content from last item
            if hasattr(last_item, "content"):
                return last_item.content
            elif hasattr(last_item, "to_dict"):
                item_dict = last_item.to_dict()
                if "content" in item_dict:
                    return item_dict["content"]
            elif isinstance(last_item, dict) and "content" in last_item:
                return last_item["content"]
            elif isinstance(last_item, str):
                return last_item

            # Can't extract, return last item as-is
            return last_item

        # Strategy 4: Object with .content attribute (e.g., Message object)
        if hasattr(result, "content"):
            return result.content

        # Strategy 5: Object with .to_dict() method
        if hasattr(result, "to_dict"):
            try:
                result_dict = result.to_dict()
                if "content" in result_dict:
                    return result_dict["content"]
                return result_dict
            except Exception as e:
                logger.debug(
                    "Failed to extract content from .to_dict() method", error=str(e)
                )

        # Strategy 6: Fallback to string conversion
        return str(result) if result is not None else ""

    # -------------------------------------------------------------------------
    # Response Detection (Structured + Heuristic)
    # -------------------------------------------------------------------------

    def _parse_structured_response(self, result: Any) -> Optional[Dict[str, Any]]:
        """Parse agent response for structured state transitions.

        Handles multiple response types:
        - dict: Direct structured response
        - str: JSON string or plain text
        - list: Array of messages/content
        - other: Images, binary data, etc.

        Structured format:
        {"state": "input-required|auth-required", "prompt": "...", ...}

        Strategy:
        1. If dict with "state" key → return directly
        2. If string → try JSON parsing
        3. If string → try regex extraction of JSON blocks
        4. Otherwise → return None (normal completion)

        Args:
            result: Agent execution result (any type)

        Returns:
            Dict with state info if structured response found, None otherwise
        """
        # Strategy 1: Direct dict response
        if isinstance(result, dict):
            if "state" in result:
                return result
            return None

        # Strategy 2: String response - try JSON parsing
        if isinstance(result, str):
            # Try parsing entire response as JSON
            try:
                parsed = json.loads(result)
                if isinstance(parsed, dict) and "state" in parsed:
                    return parsed
            except (json.JSONDecodeError, ValueError):
                pass

            # Try extracting JSON from text using regex
            json_pattern = r'\{[^{}]*"state"[^{}]*\}'
            matches = re.findall(json_pattern, result, re.DOTALL)

            for match in matches:
                try:
                    parsed = json.loads(match)
                    if isinstance(parsed, dict) and "state" in parsed:
                        return parsed
                except (json.JSONDecodeError, ValueError):
                    continue

        # Strategy 3: Other types (list, bytes, etc.) - no state transition
        return None

    def _determine_task_state(
        self, result: Any, structured: Optional[dict[str, Any]]
    ) -> tuple[TaskState, Any]:
        """Determine task state from agent response.

        Handles multiple response types:
        - Structured dict: {"state": "...", "prompt": "..."}
        - Plain string: "Hello! How can I assist you?"
        - Rich content: {"text": "...", "image": "..."}
        - Binary data: images, files, etc.

        Args:
            result: Agent execution result (any type)
            structured: Parsed structured response if available

        Returns:
            Tuple of (state, message_content)
            message_content can be str, dict, list, or any serializable type
        """
        # Check structured response first (preferred)
        if structured:
            state = structured.get("state")
            if state == "input-required":
                prompt = structured.get("prompt", self._serialize_result(result))
                return ("input-required", prompt)
            elif state == "auth-required":
                prompt = structured.get("prompt", self._serialize_result(result))
                return ("auth-required", prompt)
            elif state == app_settings.x402.status_required:
                # Keep overall task state as input-required; carry structured info forward
                return ("input-required", structured)

        # Default: task completion with any result type
        return ("completed", result)

    def _serialize_result(self, result: Any) -> str:
        """Serialize result to string for message content.

        Args:
            result: Any agent result

        Returns:
            String representation of result
        """
        if isinstance(result, str):
            return result
        elif isinstance(result, (dict, list)):
            return json.dumps(result)
        else:
            return str(result)

    # -------------------------------------------------------------------------
    # Lifecycle Notifications
    # -------------------------------------------------------------------------

    async def _notify_lifecycle(
        self, task_id: UUID, context_id: UUID, state: str, final: bool
    ) -> None:
        """Notify lifecycle changes if notifier is configured.

        Args:
            task_id: Task identifier
            context_id: Context identifier
            state: New task state
            final: Whether this is a terminal state
        """
        if self.lifecycle_notifier:
            try:
                result = self.lifecycle_notifier(task_id, context_id, state, final)
                # Handle both sync and async notifiers
                if hasattr(result, "__await__"):
                    await result
            except Exception as e:
                # Log but don't disrupt task execution on notification errors
                logger.warning(
                    "Lifecycle notification failed",
                    task_id=str(task_id),
                    context_id=str(context_id),
                    state=state,
                    error=str(e),
                )
