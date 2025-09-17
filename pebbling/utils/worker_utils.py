"""Utility classes and functions for worker operations."""

from __future__ import annotations

import uuid
from typing import Any

from pebbling.common.protocol.types import Artifact, DataPart, FilePart, Message, Part, TextPart


class MessageConverter:
    """Utility class for converting between different message formats."""

    @staticmethod
    def to_chat_format(history: list[Message]) -> list[dict[str, str]]:
        """Convert pebble protocol messages to standard chat format.

        Args:
            history: List of pebble protocol messages

        Returns:
            List of messages in standard chat format with role and content fields
        """
        message_history = []
        for message in history:
            content = MessageConverter._extract_text_content(message)
            if content:
                # Get role and convert agent to assistant for standard format
                role = message.get("role", "user")
                if role == "agent":
                    role = "assistant"

                message_history.append({"role": role, "content": content})
        return message_history

    @staticmethod
    def to_protocol_messages(result: Any, task_id: str = None, context_id: str = None) -> list[Message]:
        """Convert manifest result to pebble protocol messages.

        Args:
            result: Manifest execution result
            task_id: Optional task ID for the message
            context_id: Optional context ID for the message

        Returns:
            List of pebble protocol messages
        """
        message_id = uuid.uuid4()
        parts = PartConverter.result_to_parts(result)

        message_data = {"role": "assistant", "parts": parts, "kind": "message", "message_id": message_id}

        if task_id:
            message_data["task_id"] = task_id
        if context_id:
            message_data["context_id"] = context_id

        return [Message(**message_data)]

    @staticmethod
    def _extract_text_content(message: Message) -> str:
        """Extract text content from a pebble protocol message."""
        if "parts" not in message or not message["parts"]:
            return ""

        text_parts = [part["text"] for part in message["parts"] if part.get("kind") == "text" and "text" in part]

        return " ".join(text_parts) if text_parts else ""


class PartConverter:
    """Utility class for converting between different part formats."""

    @staticmethod
    def dict_to_part(data: dict) -> Part:
        """Convert a dictionary to the appropriate Part type.

        Args:
            data: Dictionary that may represent a Part

        Returns:
            Appropriate Part type (TextPart, FilePart, or DataPart)
        """
        kind = data.get("kind")

        if kind == "text" and "text" in data:
            return TextPart(**data)
        elif kind == "file" and "file" in data:
            return FilePart(**data)
        elif kind == "data" and "data" in data:
            return DataPart(**data)
        else:
            # Convert unknown dict to DataPart
            return DataPart(kind="data", data=data)

    @staticmethod
    def result_to_parts(result: Any) -> list[Part]:
        """Convert result to list of Parts."""
        if isinstance(result, str):
            return [TextPart(kind="text", text=result, embeddings=None)]
        elif isinstance(result, (list, tuple)):
            if all(isinstance(item, str) for item in result):
                # Handle streaming results
                return [TextPart(kind="text", text=item, embeddings=None) for item in result]
            else:
                # Handle mixed list
                parts = []
                for item in result:
                    if isinstance(item, str):
                        parts.append(TextPart(kind="text", text=item, embeddings=None))
                    elif isinstance(item, dict):
                        parts.append(PartConverter.dict_to_part(item))
                    else:
                        parts.append(TextPart(kind="text", text=str(item), embeddings=None))
                return parts
        elif isinstance(result, dict):
            return [PartConverter.dict_to_part(result)]
        else:
            # Convert other types to text representation
            return [TextPart(kind="text", text=str(result), embeddings=None)]


class ArtifactBuilder:
    """Utility class for building artifacts from results."""

    @staticmethod
    def from_result(results: Any, artifact_name: str = "result") -> list[Artifact]:
        """Convert manifest execution result to pebble protocol artifacts.

        Args:
            results: Result from manifest execution
            artifact_name: Name for the artifact

        Returns:
            List of pebble protocol artifacts
        """
        artifact_id = str(uuid.uuid4())

        # Convert result to appropriate part type
        if isinstance(results, str):
            parts = [{"kind": "text", "text": results}]
        elif isinstance(results, (list, tuple)) and all(isinstance(item, str) for item in results):
            # Handle streaming results that were collected
            parts = [{"kind": "text", "text": "\n".join(results)}]
        else:
            # Handle structured data
            parts = [{"kind": "data", "data": {"result": results}, "metadata": {"type": type(results).__name__}}]

        return [Artifact(artifact_id=artifact_id, name=artifact_name, parts=parts)]


class TaskStateManager:
    """Utility class for managing task state transitions."""

    @staticmethod
    async def validate_task_state(task: dict, expected_state: str = "submitted") -> None:
        """Validate that a task is in the expected state.

        Args:
            task: Task dictionary
            expected_state: Expected task state

        Raises:
            ValueError: If task state is not as expected
        """
        if task["status"]["state"] != expected_state:
            raise ValueError(f"Task {task['task_id']} has already been processed (state: {task['status']['state']})")

    @staticmethod
    def build_response_messages(results: Any) -> list[Message]:
        """Build response messages from results with consistent formatting."""
        response_messages: list[Message] = []

        if isinstance(results, str):
            results = [results]

        for message in results:
            parts = PartConverter.result_to_parts(message)

            if parts:
                response_messages.append(
                    Message(role="agent", parts=parts, kind="message", message_id=str(uuid.uuid4()))
                )

        return response_messages
