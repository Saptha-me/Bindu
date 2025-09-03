from __future__ import annotations as _annotations

import uuid
import inspect
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Generator
from uuid import UUID

from opentelemetry.trace import get_tracer

from pebbling.common.protocol.types import (
    Artifact, 
    Message, 
    TaskIdParams, 
    TaskSendParams,
    Part,
    TextPart,
    DataPart
)
from pebbling.penguin.manifest import AgentManifest
from pebbling.server.scheduler.base import Scheduler
from pebbling.server.storage.base import Storage

tracer = get_tracer(__name__)


@dataclass
class Worker:
    """A worker that uses an AgentManifest to execute tasks.
    
    This worker bridges the gap between the pebble task execution system
    and the manifest executor logic. It follows the same pattern as 
    pydantic-ai's AgentWorker but adapted for pebble protocol.
    """
    
    scheduler: Scheduler
    storage: Storage
    manifest: AgentManifest
    
    async def run_task(self, params: TaskSendParams) -> None:
        """Execute a task using the wrapped AgentManifest.
        
        Args:
            params: Task execution parameters containing task ID, context ID, and message
        """
        task = await self.storage.load_task(params['id'])
        if task is None:
            raise ValueError(f'Task {params["id"]} not found')
        
        # Ensure this task hasn't been run before
        if task['status']['state'] != 'submitted':
            raise ValueError(
                f'Task {params["id"]} has already been processed (state: {task["status"]["state"]})'
            )
        
        await self.storage.update_task(task['id'], state='working')
        
        try:
            # Extract message content from task
            message_content = self._extract_message_content(params['message'])
            
            # Load context for history if needed
            context = None
            if 'history_length' in params:
                history = await self.storage.load_context(params['context_id']) or []
                context = self.build_message_history(history[-params['history_length']:] if params['history_length'] else history)
            
            # Execute manifest based on its type
            result = await self._execute_manifest(message_content, context)
            
            # Convert result to artifacts
            artifacts = self.build_artifacts(result)
            
            # Convert result to messages for history
            messages = self._result_to_messages(result)
            
            await self.storage.update_task(
                task['id'], 
                state='completed', 
                new_artifacts=artifacts,
                new_messages=messages
            )
            
        except Exception:
            await self.storage.update_task(task['id'], state='failed')
            raise
    
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a running task.
        
        Args:
            params: Task identification parameters
        """
        # Update task state to canceled
        await self.storage.update_task(params['id'], state='canceled')
    
    def build_message_history(self, history: list[Message]) -> list[Any]:
        """Convert pebble protocol messages to format suitable for manifest execution.
        
        Args:
            history: List of pebble protocol messages
            
        Returns:
            List of messages in format expected by manifest
        """
        # For now, extract text content from messages
        # This can be enhanced to handle multi-part messages
        message_history = []
        for message in history:
            if 'parts' in message and message['parts']:
                text_parts = [
                    part['text'] for part in message['parts'] 
                    if part.get('kind') == 'text'
                ]
                if text_parts:
                    message_history.append(' '.join(text_parts))
        return message_history
    
    def build_artifacts(self, result: Any) -> list[Artifact]:
        """Convert manifest execution result to pebble protocol artifacts.
        
        Args:
            result: Result from manifest execution
            
        Returns:
            List of pebble protocol artifacts
        """
        artifact_id = uuid.uuid4()
        
        # Convert result to appropriate part type
        if isinstance(result, str):
            parts = [TextPart(kind='text', text=result)]
        elif isinstance(result, (list, tuple)) and all(isinstance(item, str) for item in result):
            # Handle streaming results that were collected
            parts = [TextPart(kind='text', text='\n'.join(result))]
        else:
            # Handle structured data
            parts = [DataPart(
                kind='data',
                data={'result': result},
                metadata={'type': type(result).__name__}
            )]
        
        return [Artifact(
            artifact_id=artifact_id,
            name='result',
            parts=parts
        )]
    
    def _extract_message_content(self, message: Message) -> str:
        """Extract text content from a pebble protocol message.
        
        Args:
            message: Pebble protocol message
            
        Returns:
            Extracted text content
        """
        if 'parts' not in message or not message['parts']:
            return ""
        
        text_parts = [
            part['text'] for part in message['parts']
            if part.get('kind') == 'text' and 'text' in part
        ]
        
        return ' '.join(text_parts) if text_parts else ""
    
    async def _execute_manifest(self, message_content: str, context: Any = None) -> Any:
        """Execute the manifest with the given input.
        
        Args:
            message_content: Input message content
            context: Optional execution context
            
        Returns:
            Manifest execution result
        """
        # Determine manifest execution type and call appropriately
        if inspect.isasyncgenfunction(self.manifest.run):
            # Async generator - collect all yielded values
            results = []
            async for chunk in self.manifest.run(message_content, context=context):
                results.append(chunk)
            return results
        elif inspect.iscoroutinefunction(self.manifest.run):
            # Coroutine - await single result
            return await self.manifest.run(message_content, context=context)
        elif inspect.isgeneratorfunction(self.manifest.run):
            # Generator - collect all yielded values
            return list(self.manifest.run(message_content, context=context))
        else:
            # Regular function - call directly
            return self.manifest.run(message_content, context=context)
    
    def _result_to_messages(self, result: Any) -> list[Message]:
        """Convert manifest result to pebble protocol messages.
        
        Args:
            result: Manifest execution result
            
        Returns:
            List of pebble protocol messages
        """
        message_id = str(uuid.uuid4())
        
        if isinstance(result, str):
            parts = [TextPart(kind='text', text=result)]
        elif isinstance(result, (list, tuple)) and all(isinstance(item, str) for item in result):
            # Handle streaming results
            parts = [TextPart(kind='text', text=item) for item in result]
        else:
            # Handle other result types as text representation
            parts = [TextPart(kind='text', text=str(result))]
        
        return [Message(
            role='agent',
            parts=parts,
            kind='message',
            message_id=message_id
        )]
