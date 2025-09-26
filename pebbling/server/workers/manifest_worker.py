"""ManifestWorker implementation for executing tasks using AgentManifest."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pebbling.common.protocol.types import Artifact, Message, Task, TaskIdParams, TaskSendParams
from pebbling.penguin.manifest import AgentManifest
from pebbling.server.workers.base import Worker
from pebbling.utils.worker_utils import ArtifactBuilder, MessageConverter, TaskStateManager


@dataclass
class ManifestWorker(Worker):
    """A concrete worker implementation that uses an AgentManifest to execute tasks."""

    manifest: AgentManifest

    async def run_task(self, params: TaskSendParams) -> None:
        """Execute a task using the wrapped AgentManifest.

        Args:
            params: Task execution parameters containing task ID, context ID, and message
        """
        task = await self.storage.load_task(params["task_id"])
        if task is None:
            raise ValueError(f"Task {params['task_id']} not found")

        # Validate task state
        await TaskStateManager.validate_task_state(task)

        await self.storage.update_task(task["task_id"], state="working")

        # Build complete message history
        message_history = await self._build_complete_message_history(task)

        try:
            # Execute manifest with conversation context
            # Convert message history to single string for current manifest signature
            # Agent will see conversation and infer context
            conversation_context = "\n".join(message_history) if message_history else ""
            results = self.manifest.run(conversation_context)

            # Check if agent is asking for input (contains question marks or specific patterns)
            if self._is_input_required(results):
                # A2A Protocol: Task completes with input-required state
                await self.storage.update_task(
                    task["task_id"], 
                    state="input-required",
                    metadata={"prompt": results}
                )
                # Build response message
                agent_messages = MessageConverter.to_protocol_messages(
                    results, task["task_id"], task["context_id"]
                )
                await self.storage.append_to_contexts(task["context_id"], agent_messages)
            else:
                # Normal completion
                await self._process_and_save_results(task, results)

        except Exception:
            await self.storage.update_task(task["task_id"], state="failed")
            raise

    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a running task.

        Args:
            params: Task identification parameters
        """
        await self.storage.update_task(params["task_id"], state="canceled")

    def build_message_history(self, history: list[Message]) -> list[dict[str, str]]:
        """Convert pebble protocol messages to format suitable for manifest execution."""
        return MessageConverter.to_chat_format(history)

    def build_artifacts(self, result: Any) -> list[Artifact]:
        """Convert manifest execution result to pebble protocol artifacts."""
        did_extension = self.manifest.did_extension
        return ArtifactBuilder.from_result(result, did_extension=did_extension)

    async def _build_complete_message_history(self, task: Task) -> list[dict[str, str]]:
        """Build complete message history following A2A Protocol.
        
        A2A Protocol: Use referenceTaskIds to understand conversation flow.
        If present, prioritize referenced tasks. Otherwise, use context.
        """
        # Check if this task has referenceTaskIds (A2A Protocol)
        current_message = task.get("history", [])[0] if task.get("history") else None
        reference_task_ids = []
        
        if current_message and "reference_task_ids" in current_message:
            reference_task_ids = current_message["reference_task_ids"]
        
        if reference_task_ids:
            # A2A Protocol: Build history from referenced tasks
            referenced_messages = []
            for task_id in reference_task_ids:
                ref_task = await self.storage.load_task(task_id)
                if ref_task and ref_task.get("history"):
                    referenced_messages.extend(ref_task["history"])
            
            # Add current task messages
            current_messages = task.get("history", [])
            all_messages = referenced_messages + current_messages
            
        else:
            # Fallback: Use context-based history (all tasks in context)
            tasks_by_context = await self.storage.list_tasks_by_context(task["context_id"])
            
            # Filter out the current task to avoid duplication
            previous_tasks = [t for t in tasks_by_context if t["task_id"] != task["task_id"]]
            
            # Build history from all previous tasks
            all_previous_messages = []
            for prev_task in previous_tasks:
                history = prev_task.get("history", [])
                if history:
                    all_previous_messages.extend(history)
            
            # Get current task messages
            current_messages = task.get("history", [])
            all_messages = all_previous_messages + current_messages
        
        return self.build_message_history(all_messages) if all_messages else []

    def _normalize_message_order(self, message: dict) -> dict:
        """Normalize message field order for consistency."""
        return {
            "context_id": message.get("context_id"),
            "task_id": message.get("task_id"),
            "message_id": message.get("message_id"),
            "kind": message.get("kind"),
            "parts": message.get("parts"),
            "role": message.get("role"),
        }

    def _normalize_messages(self, messages: list) -> list:
        """Normalize a list of messages to have consistent field ordering."""
        return [self._normalize_message_order(msg) for msg in messages]

    async def _process_and_save_results(self, task: dict, results: Any) -> None:
        """Process results and save to storage."""
        # Convert agent response to message format
        agent_messages = MessageConverter.to_protocol_messages(results, task["task_id"], task["context_id"])

        # Normalize messages for consistency
        normalized_agent_messages = self._normalize_messages(agent_messages)

        # Update context with new agent messages only (task history already in context)
        await self.storage.append_to_contexts(task["context_id"], normalized_agent_messages)

        # Build artifacts from results
        artifacts = self.build_artifacts(results)

        # Update task with completion
        await self.storage.update_task(
            task["task_id"], state="completed", new_artifacts=artifacts, new_messages=normalized_agent_messages
        )
    
    def _is_input_required(self, result: Any) -> bool:
        """Detect if agent response indicates need for user input.
        
        A2A Protocol: Agent asking questions means task needs input.
        """
        if isinstance(result, str):
            # Simple heuristic: questions often contain these patterns
            input_indicators = [
                "?",  # Question mark
                "please specify",
                "could you",
                "would you like",
                "what style",
                "which",
                "tell me more",
                "provide more details"
            ]
            result_lower = result.lower()
            return any(indicator in result_lower for indicator in input_indicators)
        return False
