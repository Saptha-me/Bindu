"""Optimized utility classes for worker operations and message conversion."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional, Union
from uuid import UUID, uuid4

from bindu.common.protocol.types import (
    Artifact,
    DataPart,
    FilePart,
    Message,
    Part,
    TextPart,
)
from bindu.settings import app_settings

if TYPE_CHECKING:
    from bindu.extensions.did import DIDAgentExtension

# Type aliases for better readability
ChatMessage = dict[str, str]
ProtocolMessage = Message


class MessageConverter:
    """Optimized converter for message format transformations."""

    # Role mapping for chat format conversion
    ROLE_MAP = {"agent": "assistant", "user": "user"}

    @staticmethod
    def to_chat_format(history: list[Message]) -> list[ChatMessage]:
        """Convert protocol messages to standard chat format.

        Args:
            history: List of protocol messages

        Returns:
            List of chat messages with role and content fields
        """
        return [
            {
                "role": MessageConverter.ROLE_MAP.get(msg.get("role", "user"), "user"),
                "content": content,
            }
            for msg in history
            if (content := MessageConverter._extract_text_content(msg))
        ]

    @staticmethod
    def to_protocol_messages(
        result: Any,
        task_id: Optional[Union[str, UUID]] = None,
        context_id: Optional[Union[str, UUID]] = None,
    ) -> list[ProtocolMessage]:
        """Convert manifest result to protocol messages.

        Args:
            result: Manifest execution result
            task_id: Optional task ID
            context_id: Optional context ID

        Returns:
            List of protocol messages
        """
        message_data: dict[str, Any] = {
            "role": "assistant",
            "parts": PartConverter.result_to_parts(result),
            "kind": "message",
            "message_id": uuid4(),
        }

        if task_id:
            message_data["task_id"] = task_id
        if context_id:
            message_data["context_id"] = context_id

        return [Message(**message_data)]

    @staticmethod
    def _extract_text_content(message: Message) -> str:
        """Extract text content from protocol message."""
        parts = message.get("parts", [])
        if not parts:
            return ""

        # Use generator for memory efficiency
        text_parts = (
            part["text"]
            for part in parts
            if part.get("kind") == "text" and "text" in part
        )
        return " ".join(text_parts)


class PartConverter:
    """Optimized converter for Part type transformations."""

    # Part type mapping for efficient lookup
    PART_TYPES = {
        "text": (TextPart, "text"),
        "file": (FilePart, "file"),
        "data": (DataPart, "data"),
    }

    @staticmethod
    def dict_to_part(data: dict[str, Any]) -> Part:
        """Convert dictionary to appropriate Part type.

        Args:
            data: Dictionary representing a Part

        Returns:
            Appropriate Part type (TextPart, FilePart, or DataPart)
        """
        kind = data.get("kind")

        if kind in PartConverter.PART_TYPES:
            part_class, required_field = PartConverter.PART_TYPES[kind]
            if required_field in data:
                return part_class(**data)

        # Fallback: convert unknown dict to DataPart
        return DataPart(kind="data", data=data)

    @staticmethod
    def result_to_parts(result: Any) -> list[Part]:
        """Convert result to list of Parts with optimized type checking."""
        # Fast path for strings
        if isinstance(result, str):
            return [TextPart(kind="text", text=result)]

        # Handle sequences
        if isinstance(result, (list, tuple)):
            # Check if all items are strings (common case)
            if result and all(isinstance(item, str) for item in result):
                return [TextPart(kind="text", text=item) for item in result]

            # Handle mixed types
            parts: list[Part] = []
            for item in result:
                if isinstance(item, str):
                    parts.append(TextPart(kind="text", text=item))
                elif isinstance(item, dict):
                    parts.append(PartConverter.dict_to_part(item))
                else:
                    parts.append(TextPart(kind="text", text=str(item)))
            return parts

        # Handle dictionaries
        if isinstance(result, dict):
            return [PartConverter.dict_to_part(result)]

        # Fallback: convert to text
        return [TextPart(kind="text", text=str(result))]


class ArtifactBuilder:
    """Optimized builder for creating artifacts from results."""

    @staticmethod
    def from_result(
        results: Any,
        artifact_name: str = "result",
        did_extension: Optional["DIDAgentExtension"] = None,
    ) -> list[Artifact]:
        """Convert execution result to protocol artifacts.

        Args:
            results: Result from manifest execution
            artifact_name: Name for the artifact
            did_extension: Optional DID extension for signing

        Returns:
            List of protocol artifacts
        """
        # Convert result to appropriate part type
        if isinstance(results, str):
            parts = [{"kind": "text", "text": results}]
        elif (
            isinstance(results, (list, tuple))
            and results
            and all(isinstance(item, str) for item in results)
        ):
            # Join streaming results efficiently
            parts = [{"kind": "text", "text": "\n".join(results)}]
        else:
            # Structured data
            parts = [{"kind": "data", "data": {"result": results}}]

        # Apply DID signing if available
        if did_extension:
            metadata_key = app_settings.did.agent_extension_metadata
            for part in parts:
                if part.get("kind") == "text" and "text" in part:
                    part.setdefault("metadata", {})[metadata_key] = (
                        did_extension.sign_text(part["text"])
                    )

        return [Artifact(artifact_id=uuid4(), name=artifact_name, parts=parts)]


class TaskStateManager:
    """Optimized manager for task state transitions and validation."""

    @staticmethod
    async def validate_task_state(
        task: dict[str, Any], expected_state: str = "submitted"
    ) -> None:
        """Validate task is in expected state.

        Args:
            task: Task dictionary
            expected_state: Expected task state

        Raises:
            ValueError: If task state doesn't match expected
        """
        current_state = task["status"]["state"]
        if current_state != expected_state:
            raise ValueError(
                f"Task {task['task_id']} already processed (state: {current_state}, expected: {expected_state})"
            )

    @staticmethod
    def build_response_messages(results: Any) -> list[Message]:
        """Build response messages from results with optimized formatting."""
        # Normalize to list
        messages_list = [results] if isinstance(results, str) else results

        # Build messages efficiently using list comprehension
        return [
            Message(role="agent", parts=parts, kind="message", message_id=uuid4())
            for msg in messages_list
            if (parts := PartConverter.result_to_parts(msg))
        ]
