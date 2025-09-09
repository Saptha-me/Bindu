"""ManifestWorker implementation for executing tasks using AgentManifest."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pebbling.common.protocol.types import (
    Artifact,
    Message,
    TaskIdParams,
    TaskSendParams
)
from pebbling.penguin.manifest import AgentManifest
from pebbling.server.workers.base import Worker
from pebbling.utils.worker_utils import (
    MessageConverter,
    ArtifactBuilder,
    TaskStateManager
)


@dataclass
class ManifestWorker(Worker):
    """A concrete worker implementation that uses an AgentManifest to execute tasks."""
    
    manifest: AgentManifest
    
    async def run_task(self, params: TaskSendParams) -> None:
        """Execute a task using the wrapped AgentManifest.
        
        Args:
            params: Task execution parameters containing task ID, context ID, and message
        """
        task = await self.storage.load_task(params['task_id'])
        if task is None:
            raise ValueError(f'Task {params["task_id"]} not found')
        
        # Validate task state
        await TaskStateManager.validate_task_state(task)
        
        await self.storage.update_task(task['task_id'], state='working')

        # Build complete message history
        message_history = await self._build_complete_message_history(task)
        
        try:
            # Execute manifest
            results = self.manifest.run(message_history)

            # Process and save results
            await self._process_and_save_results(task, results)

        except Exception:
            await self.storage.update_task(task['task_id'], state='failed')
            raise   
    
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a running task.
        
        Args:
            params: Task identification parameters
        """
        await self.storage.update_task(params['task_id'], state='canceled')
    
    def build_message_history(self, history: list[Message]) -> list[dict[str, str]]:
        """Convert pebble protocol messages to format suitable for manifest execution."""
        return MessageConverter.to_chat_format(history)
    
    def build_artifacts(self, results: Any) -> list[Artifact]:
        """Convert manifest execution result to pebble protocol artifacts."""
        return ArtifactBuilder.from_result(results)
    
    async def _build_complete_message_history(self, task: dict) -> list[dict[str, str]]:
        """Build complete message history combining existing context with current message."""
        # Load existing context as list of messages
        existing_context = await self.storage.load_context(task['context_id']) or []
        
        # Build message history from task history (current user message)
        current_message_history = self.build_message_history(task.get('history', []))
        
        # Combine existing conversation history with current message
        if isinstance(existing_context, list) and existing_context:
            # existing_context contains the full conversation history from previous calls
            previous_history = self.build_message_history(existing_context)
            return previous_history + current_message_history
        else:
            # First message in context
            return current_message_history
    
    def _normalize_message_order(self, message: dict) -> dict:
        """Normalize message field order for consistency."""
        return {
            'context_id': message.get('context_id'),
            'task_id': message.get('task_id'),
            'message_id': message.get('message_id'),
            'kind': message.get('kind'),
            'parts': message.get('parts'),
            'role': message.get('role')
        }
    
    def _normalize_messages(self, messages: list) -> list:
        """Normalize a list of messages to have consistent field ordering."""
        return [self._normalize_message_order(msg) for msg in messages]

    async def _process_and_save_results(self, task: dict, results: Any) -> None:
        """Process results and save to storage."""
        # Convert agent response to message format and append to history
        agent_messages = MessageConverter.to_protocol_messages(
            results, task['task_id'], task['context_id']
        )
        
        # Load existing context to preserve full conversation history
        existing_context = await self.storage.load_context(task['context_id']) or []
        
        # Normalize all messages to have consistent field ordering
        normalized_existing = self._normalize_messages(existing_context)
        normalized_current = self._normalize_messages(task.get('history', []))
        normalized_agent = self._normalize_messages(agent_messages)
        
        # Build complete conversation history: existing + current task + new agent response
        complete_history = normalized_existing + normalized_current + normalized_agent
        
        # Save complete conversation history to context for future calls
        await self.storage.update_context(task['context_id'], complete_history)

        # Process results and convert to messages
        response_messages = TaskStateManager.build_response_messages(results)
        
        # Build artifacts
        artifacts = self.build_artifacts(results)

        # Update task with completion
        await self.storage.update_task(
            task['task_id'], 
            state='completed', 
            new_artifacts=artifacts, 
            new_messages=response_messages
        )
