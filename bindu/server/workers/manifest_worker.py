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
from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import UUID

from bindu.common.protocol.types import Artifact, Message, Task, TaskIdParams, TaskSendParams, TaskState
from bindu.penguin.manifest import AgentManifest
from bindu.server.workers.base import Worker
from bindu.settings import app_settings
from bindu.utils.worker_utils import ArtifactBuilder, MessageConverter, TaskStateManager


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
        await self.storage.update_task(task["task_id"], state="working")

        # Step 2: Build conversation history (A2A Protocol)
        message_history = await self._build_complete_message_history(task)

        try:
            # Step 3: Execute manifest with system prompt (if enabled)
            if app_settings.agent.enable_structured_responses:
                # Inject structured response system prompt
                system_prompt = app_settings.agent.structured_response_system_prompt
                if message_history:
                    conversation_context = f"system: {system_prompt}\n" + "\n".join(
                        f"{msg['role']}: {msg['content']}" for msg in message_history
                    )
                else:
                    conversation_context = f"system: {system_prompt}"
            else:
                # No system prompt injection
                conversation_context = "\n".join(
                    f"{msg['role']}: {msg['content']}" for msg in message_history
                ) if message_history else ""
            
            results = self.manifest.run(conversation_context)

            # Step 4: Parse response and detect state
            structured_response = self._parse_structured_response(results)
            
            # Determine task state based on response
            state, metadata, message_content = self._determine_task_state(
                results, structured_response
            )
            
            if state in ("input-required", "auth-required"):
                # Hybrid Pattern: Return Message only, keep task open
                await self._handle_intermediate_state(task, state, metadata, message_content)
            else:
                # Hybrid Pattern: Task complete - generate Message + Artifacts
                await self._handle_terminal_state(task, results, state)

        except Exception as e:
            # Handle task failure with error message
            await self._handle_task_failure(task, str(e))
            raise

    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a running task.

        Args:
            params: Task identification parameters containing task_id
        """
        await self.storage.update_task(params["task_id"], state="canceled")

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
            
        else:
            # Strategy 2: Context-based history (implicit continuation)
            tasks_by_context = await self.storage.list_tasks_by_context(task["context_id"])
            previous_tasks = [t for t in tasks_by_context if t["task_id"] != task["task_id"]]
            
            all_previous_messages: list[Message] = []
            for prev_task in previous_tasks:
                history = prev_task.get("history", [])
                if history:
                    all_previous_messages.extend(history)
            
            current_messages = task.get("history", [])
            all_messages = all_previous_messages + current_messages
        
        return self.build_message_history(all_messages) if all_messages else []

    # -------------------------------------------------------------------------
    # Message Normalization
    # -------------------------------------------------------------------------

    async def _handle_intermediate_state(
        self, 
        task: dict[str, Any], 
        state: TaskState, 
        metadata: dict[str, Any],
        message_content: str
    ) -> None:
        """Handle intermediate task states (input-required, auth-required).

        Args:
            task: Current task
            state: Task state to set
            metadata: Metadata to store with task
            message_content: Content for agent message
        """
        await self.storage.update_task(task["task_id"], state=state, metadata=metadata)
        
        agent_messages = MessageConverter.to_protocol_messages(
            message_content, task["task_id"], task["context_id"]
        )
        await self.storage.append_to_contexts(task["context_id"], agent_messages)

    # -------------------------------------------------------------------------
    # Terminal State Handling
    # -------------------------------------------------------------------------

    async def _handle_terminal_state(
        self, 
        task: dict[str, Any], 
        results: Any,
        state: TaskState = "completed"
    ) -> None:
        """Handle terminal task states (completed/failed).
        
        Hybrid Pattern - Terminal States:
        - completed: Message (explanation) + Artifacts (deliverable)
        - failed: Message (error explanation) only, NO artifacts
        - canceled: State change only, NO new content

        Args:
            task: Task dict being finalized
            results: Agent execution results
            state: Terminal state (completed or failed)
        """
        if state == "completed":
            # Success: Add both Message and Artifacts
            agent_messages = MessageConverter.to_protocol_messages(
                results, task["task_id"], task["context_id"]
            )
            await self.storage.append_to_contexts(task["context_id"], agent_messages)
            
            artifacts = self.build_artifacts(results)
            await self.storage.update_task(
                task["task_id"], 
                state="completed", 
                new_artifacts=artifacts, 
                new_messages=agent_messages
            )
        
        elif state == "failed":
            # Failure: Message only (error explanation), NO artifacts
            error_message = MessageConverter.to_protocol_messages(
                results, task["task_id"], task["context_id"]
            )
            await self.storage.append_to_contexts(task["context_id"], error_message)
            await self.storage.update_task(
                task["task_id"], 
                state="failed", 
                new_messages=error_message
            )
    
    async def _handle_task_failure(self, task: dict[str, Any], error: str) -> None:
        """Handle task execution failure.
        
        Creates an error message and marks task as failed without artifacts.

        Args:
            task: Task that failed
            error: Error description
        """
        error_message = MessageConverter.to_protocol_messages(
            f"Task execution failed: {error}", 
            task["task_id"], 
            task["context_id"]
        )
        await self.storage.append_to_contexts(task["context_id"], error_message)
        await self.storage.update_task(
            task["task_id"], 
            state="failed", 
            new_messages=error_message
        )
    
    # -------------------------------------------------------------------------
    # Response Detection (Structured + Heuristic)
    # -------------------------------------------------------------------------

    def _parse_structured_response(self, result: Any) -> Optional[Dict[str, Any]]:
        """Parse agent response for structured state transitions.
        
        Attempts to extract JSON with format:
        {"state": "input-required|auth-required", "prompt": "...", ...}

        Strategy:
        1. Try parsing entire response as JSON
        2. Fall back to regex extraction of JSON blocks
        3. Return None if no structured response found

        Args:
            result: Agent execution result

        Returns:
            Dict with state info if structured response found, None otherwise
        """
        if not isinstance(result, str):
            return None

        # Strategy 1: Parse entire response as JSON
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict) and "state" in parsed:
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

        # Strategy 2: Extract JSON from text using regex
        json_pattern = r'\{[^{}]*"state"[^{}]*\}'
        matches = re.findall(json_pattern, result, re.DOTALL)
        
        for match in matches:
            try:
                parsed = json.loads(match)
                if isinstance(parsed, dict) and "state" in parsed:
                    return parsed
            except (json.JSONDecodeError, ValueError):
                continue
        
        return None
    
    def _determine_task_state(
        self, 
        result: Any, 
        structured: Optional[dict[str, Any]]
    ) -> tuple[TaskState, dict[str, Any], str]:
        """Determine task state from agent response.

        Args:
            result: Agent execution result
            structured: Parsed structured response if available

        Returns:
            Tuple of (state, metadata, message_content)
        """
        # Check structured response first (preferred)
        if structured:
            state = structured.get("state")
            if state == "input-required":
                return (
                    "input-required",
                    {"prompt": structured.get("prompt", result)},
                    structured.get("prompt", result)
                )
            elif state == "auth-required":
                metadata = {
                    "auth_prompt": structured.get("prompt", result),
                    "auth_type": structured.get("auth_type"),
                    "service": structured.get("service")
                }
                # Remove None values
                metadata = {k: v for k, v in metadata.items() if v is not None}
                return ("auth-required", metadata, metadata["auth_prompt"])
        
        # Heuristic detection (backward compatibility)
        if isinstance(result, str):
            result_lower = result.lower()
            
            # Check for auth indicators
            auth_indicators = ["authentication required", "unauthorized", "api key required"]
            if any(indicator in result_lower for indicator in auth_indicators):
                return ("auth-required", {"auth_prompt": result}, result)
            
            # Check for input indicators
            input_indicators = ["?", "please specify", "could you", "would you like"]
            if any(indicator in result_lower for indicator in input_indicators):
                return ("input-required", {"prompt": result}, result)
        
        # Default: task completion
        return ("completed", {}, result)
