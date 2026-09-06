"""Message format conversion utilities for worker operations."""

from __future__ import annotations

import base64
import io
from functools import lru_cache
from typing import Any, Optional, Union
from uuid import UUID, uuid4

from pypdf import PdfReader
from docx import Document

from bindu.common.protocol.types import Message, Part
from bindu.utils.logging import get_logger

# Import PartConverter from same package
from .parts import PartConverter

logger = get_logger("bindu.utils.worker.messages")

# Type aliases for better readability
ChatMessage = dict[str, str]
ProtocolMessage = Message


class FileInterceptor:
    """Native pipeline for intercepting and parsing Base64 file parts."""

    SUPPORTED_MIME_TYPES = {
        "application/pdf",
        "text/plain",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    @staticmethod
    def _extract_pdf(file_bytes: bytes) -> str:
        """Extract text from a PDF buffer."""
        try:
            reader = PdfReader(io.BytesIO(file_bytes))
            return "\n".join(page.extract_text() for page in reader.pages)
        except Exception as e:
            logger.error(f"Failed to parse PDF: {e}")
            return "[Error: Could not parse PDF content]"

    @staticmethod
    def _extract_docx(file_bytes: bytes) -> str:
        """Extract text from a DOCX buffer."""
        try:
            doc = Document(io.BytesIO(file_bytes))
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
        except Exception as e:
            logger.error(f"Failed to parse DOCX: {e}")
            return "[Error: Could not parse DOCX content]"

    @classmethod
    def intercept_and_parse(cls, parts: list[Part]) -> list[dict[str, Any]]:
        """Intercept file parts, extract text, and replace with text parts."""
        processed_parts = []

        for part in parts:
            if part.get("kind") != "file":
                processed_parts.append(part)
                continue

            # A2A FilePart shape: {"kind": "file", "file": {"bytes", "mimeType", "name"}}
            file_obj = part.get("file") or {}
            mime_type = file_obj.get("mimeType", "")
            base64_data = str(file_obj.get("bytes", ""))

            if not base64_data:
                # FileWithUri (or missing bytes): nothing to decode locally.
                # Say so explicitly instead of emitting an empty "Document
                # Uploaded" block from b64decode("").
                ref = file_obj.get("uri") or file_obj.get("name") or "unknown"
                logger.warning(f"File part without inline bytes skipped: {ref}")
                processed_parts.append(
                    {
                        "kind": "text",
                        "text": f"[File reference not fetched: {ref}]",
                    }
                )
                continue

            if mime_type not in cls.SUPPORTED_MIME_TYPES:
                logger.warning(f"Unsupported MIME type rejected: {mime_type}")
                processed_parts.append(
                    {
                        "kind": "text",
                        "text": f"[Unsupported file type: {mime_type}]",
                    }
                )
                continue

            try:
                extracted_text = _extract_file_text(mime_type, base64_data)

                # Inject the parsed document as a formatted text prompt
                processed_parts.append(
                    {
                        "kind": "text",
                        "text": f"--- Document Uploaded ---\n{extracted_text}\n--- End of Document ---",
                    }
                )

            except Exception as e:
                logger.error(f"Base64 decoding or routing failed: {e}")
                processed_parts.append(
                    {
                        "kind": "text",
                        "text": "[System: Failed to decode uploaded file data]",
                    }
                )

        return processed_parts


@lru_cache(maxsize=8)
def _extract_file_text(mime_type: str, base64_data: str) -> str:
    """Decode and extract text from a supported file payload.

    Cached because task history is append-only: on a multi-turn
    conversation every turn re-flattens the full history, and without the
    cache the same PDF is base64-decoded and re-parsed on every turn,
    synchronously on the event loop. Failures are not cached (lru_cache
    only stores successful returns).
    """
    file_bytes = base64.b64decode(base64_data)
    if mime_type == "application/pdf":
        return FileInterceptor._extract_pdf(file_bytes)
    if mime_type == "text/plain":
        return file_bytes.decode("utf-8")
    return FileInterceptor._extract_docx(file_bytes)


class MessageConverter:
    """Optimized converter for message format transformations."""

    ROLE_MAP = {"agent": "assistant", "user": "user", "system": "system"}

    @staticmethod
    def to_chat_format(history: list[Message]) -> list[ChatMessage]:
        """Convert protocol messages to standard chat format.

        Now intercepts Base64 files natively and converts them to text parts
        before passing them to the agent framework.
        """
        result = []
        for msg in history:
            original_parts = msg.get("parts", [])
            if not original_parts:
                continue

            # INTERCEPTOR: Parse files into text natively
            processed_parts = FileInterceptor.intercept_and_parse(original_parts)

            role = MessageConverter.ROLE_MAP.get(msg.get("role", "user"), "user")

            # Since all files are now parsed into text, we safely extract it
            content = MessageConverter._extract_text_content(processed_parts)
            if content:
                result.append({"role": role, "content": content})

        return result

    @staticmethod
    def to_protocol_messages(
        result: Any,
        task_id: Optional[Union[str, UUID]] = None,
        context_id: Optional[Union[str, UUID]] = None,
    ) -> list[ProtocolMessage]:
        """Convert manifest result to protocol messages."""
        return [
            Message(
                role="agent",
                parts=PartConverter.result_to_parts(result),
                kind="message",
                message_id=uuid4(),
                task_id=task_id
                if isinstance(task_id, UUID)
                else (UUID(task_id) if task_id else uuid4()),
                context_id=context_id
                if isinstance(context_id, UUID)
                else (UUID(context_id) if context_id else uuid4()),
            )
        ]

    @staticmethod
    def _extract_text_content(parts: list[dict[str, Any]]) -> str:
        """Extract text content from processed parts."""
        if not parts:
            return ""

        text_parts = (
            part["text"]
            for part in parts
            if part.get("kind") == "text" and "text" in part
        )
        return " ".join(text_parts)
