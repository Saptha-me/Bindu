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
            # Execute manifest
            results = self.manifest.run(message_history)

            # Process and save results
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

    def build_artifacts(self, results: Any) -> list[Artifact]:
        """Convert manifest execution result to pebble protocol artifacts."""
        return ArtifactBuilder.from_result(results)

    async def _build_complete_message_history(self, task: Task) -> list[dict[str, str]]:
        """Build complete message history combining existing context with current message."""
        tasks_by_context = await self.storage.list_tasks_by_context(task["context_id"])

        # Filter out the current task to avoid duplication
        previous_tasks = [t for t in tasks_by_context if t["task_id"] != task["task_id"]]

        # Early return if no previous tasks
        if not previous_tasks:
            return self.build_message_history(task.get("history", []))

        # Flatten all previous task histories efficiently
        all_previous_messages = []
        for prev_task in previous_tasks:
            history = prev_task.get("history", [])
            if history:  # Only extend if history exists
                all_previous_messages.extend(history)

        # Get current task messages
        current_messages = task.get("history", [])

        # Combine and convert all messages in one operation
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
