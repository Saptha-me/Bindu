from __future__ import annotations as _annotations

import uuid
import inspect
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Generator, AsyncIterator
from uuid import UUID
from contextlib import asynccontextmanager

import anyio
from opentelemetry.trace import get_tracer, use_span

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
class Worker(ABC):
    """A worker that uses an AgentManifest to execute tasks.
    
    This worker bridges the gap between the pebble task execution system
    and the manifest executor logic. It follows the Pebble pattern for
    proper lifecycle management.
    """
    
    scheduler: Scheduler
    storage: Storage

    @asynccontextmanager
    async def run(self) -> AsyncIterator[None]:
        """Run the worker.

        It connects to the scheduler, and it makes itself available to receive commands.
        """
        async with anyio.create_task_group() as tg:
            tg.start_soon(self._loop)
            yield
            tg.cancel_scope.cancel()

    async def _loop(self) -> None:
        """Main worker loop to process tasks from scheduler."""
        async for task_operation in self.scheduler.receive_task_operations():
            await self._handle_task_operation(task_operation)

    async def _handle_task_operation(self, task_operation) -> None:
        """Handle a task operation from the scheduler."""
        try:
            with use_span(task_operation['_current_span']):
                with tracer.start_as_current_span(
                    f'{task_operation["operation"]} task', attributes={'logfire.tags': ['pebble']}
                ):
                    if task_operation['operation'] == 'run':
                        await self.run_task(task_operation['params'])
                    elif task_operation['operation'] == 'cancel':
                        await self.cancel_task(task_operation['params'])
                    elif task_operation['operation'] == 'pause':
                        # Handle pause if implemented
                        pass
                    elif task_operation['operation'] == 'resume':
                        # Handle resume if implemented
                        pass
        except Exception:
            # Update task status to failed on any exception
            task_id = task_operation['params']['id']
            await self.storage.update_task(task_id, state='failed')

    @abstractmethod
    async def run_task(self, params: TaskSendParams) -> None:
        """Execute a task."""
        ...

    @abstractmethod
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a running task."""
        ...

    @abstractmethod
    def build_message_history(self, history: list[Message]) -> list[Any]:
        """Convert pebble protocol messages to format suitable for manifest execution."""
        ...

    @abstractmethod
    def build_artifacts(self, result: Any) -> list[Artifact]:
        """Convert manifest execution result to pebble protocol artifacts."""
        ...


@dataclass
class ManifestWorker(Worker):
    """A concrete worker implementation that uses an AgentManifest to execute tasks."""
    
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
