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
    FilePart,
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
        task = await self.storage.load_task(params['task_id'])
        if task is None:
            raise ValueError(f'Task {params["task_id"]} not found')
        
        # Ensure this task hasn't been run before
        if task['status']['state'] != 'submitted':
            raise ValueError(
                f'Task {params["task_id"]} has already been processed (state: {task["status"]["state"]})'
            )
        
        await self.storage.update_task(task['task_id'], state='working')

        message_history = await self.storage.load_context(task['context_id']) or []
        message_history.extend(self.build_message_history(task.get('history', [])))
        
        try:
            # Execute manifest based on its type
            results = await self._execute_manifest(message_history)

            await self.storage.update_context(task['context_id'], results)

            # Process results and convert to messages
            # messages: The conversation transcript ("Here's how I solved it...")
            response_messages: list[Message] = []
            
            for message in results:
                _parts: list[Part] = []
                
                if isinstance(message, str):
                    _parts.append(TextPart(kind='text', text=message))
                elif isinstance(message, list):
                    # Handle list of strings or parts
                    for part in message:
                        if isinstance(part, str):
                            _parts.append(TextPart(kind='text', text=part))
                        elif isinstance(part, dict):
                            _parts.append(self._dict_to_part(part))
                        else:
                            _parts.append(TextPart(kind='text', text=str(part)))
                elif isinstance(message, dict):
                    _parts.append(self._dict_to_part(message))
                else:
                    # Convert other types to text representation
                    _parts.append(TextPart(kind='text', text=str(message)))
                
                if _parts:
                    response_messages.append(Message(
                        role='agent',
                        parts=_parts,
                        kind='message',
                        message_id=str(uuid.uuid4())
                    ))
            
            # artifacts: The actual solution/deliverable ("Here's the code/analysis/result")
            artifacts = self.build_artifacts(results)

        except Exception:
            await self.storage.update_task(task['task_id'], state='failed')
            raise   
    
        else:
            await self.storage.update_task(
                task['task_id'], state='completed', new_artifacts=artifacts, new_messages=response_messages
            )
    
    async def cancel_task(self, params: TaskIdParams) -> None:
        """Cancel a running task.
        
        Args:
            params: Task identification parameters
        """
        # Update task state to canceled
        await self.storage.update_task(params['task_id'], state='canceled')
    
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
    
    def build_artifacts(self, results: Any) -> list[Artifact]:
        """Convert manifest execution result to pebble protocol artifacts.
        
        Args:
            results: Result from manifest execution
            
        Returns:
            List of pebble protocol artifacts
        """
        artifact_id = str(uuid.uuid4())
        
        # Convert result to appropriate part type
        if isinstance(results, str):
            parts = [{'kind': 'text', 'text': results}]
        elif isinstance(results, (list, tuple)) and all(isinstance(item, str) for item in results):
            # Handle streaming results that were collected
            parts = [{'kind': 'text', 'text': '\n'.join(results)}]
        else:
            # Handle structured data
            parts = [{'kind': 'data', 'data': {'result': results}, 'metadata': {'type': type(results).__name__}}]
        
        return [Artifact(
            artifact_id=artifact_id,
            name='result',
            parts=parts
        )]
    
    def _dict_to_part(self, data: dict) -> Part:
        """Convert a dictionary to the appropriate Part type based on its structure.
        
        Args:
            data: Dictionary that may represent a Part
            
        Returns:
            Appropriate Part type (TextPart, FilePart, or DataPart)
        """
        kind = data.get('kind')
        
        if kind == 'text' and 'text' in data:
            return TextPart(**data)
        elif kind == 'file' and 'file' in data:
            return FilePart(**data)
        elif kind == 'data' and 'data' in data:
            return DataPart(**data)
        else:
            # Convert unknown dict to DataPart
            return DataPart(kind='data', data=data)
    
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
    
    async def _execute_manifest(self, message_history: list[str]) -> Any:
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
            async for chunk in self.manifest.run(message_history):
                results.append(chunk)
            return results
        elif inspect.iscoroutinefunction(self.manifest.run):
            # Coroutine - await single result
            return await self.manifest.run(message_history)
        elif inspect.isgeneratorfunction(self.manifest.run):
            # Generator - collect all yielded values
            return list(self.manifest.run(message_history))
        else:
            # Regular function - call directly
            return self.manifest.run(message_history)
    
    def _result_to_messages(self, result: Any) -> list[Message]:
        """Convert manifest result to pebble protocol messages.
        
        Args:
            result: Manifest execution result
            
        Returns:
            List of pebble protocol messages
        """
        message_id = str(uuid.uuid4())
        
        if isinstance(result, str):
            parts = [{'kind': 'text', 'text': result}]
        elif isinstance(result, (list, tuple)) and all(isinstance(item, str) for item in result):
            # Handle streaming results
            parts = [{'kind': 'text', 'text': item} for item in result]
        else:
            # Handle other result types as text representation
            parts = [{'kind': 'text', 'text': str(result)}]
        
        return [Message(
            role='agent',
            parts=parts,
            kind='message',
            message_id=message_id
        )]
