"""Tests for worker message utilities."""

from typing import cast

from bindu.common.protocol.types import Message
from bindu.utils.worker.messages import MessageConverter


class TestMessageConverter:
    """Test MessageConverter functionality."""

    def test_to_chat_format_with_user_message(self):
        """Test converting user message to chat format."""
        messages = [
            cast(
                Message, {"role": "user", "parts": [{"kind": "text", "text": "Hello"}]}
            )
        ]

        result = MessageConverter.to_chat_format(messages)

        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"

    def test_to_chat_format_with_agent_message(self):
        """Test converting agent message to assistant role."""
        messages = [
            cast(
                Message,
                {"role": "agent", "parts": [{"kind": "text", "text": "Hi there"}]},
            )
        ]

        result = MessageConverter.to_chat_format(messages)

        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert result[0]["content"] == "Hi there"

    def test_to_chat_format_with_conversation(self):
        """Test converting conversation to chat format."""
        messages = [
            cast(
                Message,
                {"role": "user", "parts": [{"kind": "text", "text": "Question?"}]},
            ),
            cast(
                Message,
                {"role": "agent", "parts": [{"kind": "text", "text": "Answer."}]},
            ),
            cast(
                Message,
                {"role": "user", "parts": [{"kind": "text", "text": "Follow-up?"}]},
            ),
        ]

        result = MessageConverter.to_chat_format(messages)

        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[2]["role"] == "user"

    def test_to_chat_format_with_empty_list(self):
        """Test converting empty message list."""
        result = MessageConverter.to_chat_format([])

        assert result == []

    def test_to_chat_format_with_multiple_text_parts(self):
        """Test converting message with multiple text parts."""
        messages = [
            cast(
                Message,
                {
                    "role": "user",
                    "parts": [
                        {"kind": "text", "text": "Part 1"},
                        {"kind": "text", "text": "Part 2"},
                    ],
                },
            )
        ]

        result = MessageConverter.to_chat_format(messages)

        assert len(result) == 1
        assert "content" in result[0]

    def test_to_chat_format_skips_messages_without_parts(self):
        """Test that messages without parts are skipped."""
        messages = [cast(Message, {"role": "user"})]

        result = MessageConverter.to_chat_format(messages)

        assert result == []

    def test_to_chat_format_extracts_text_from_a2a_file_part(self):
        """File bytes live at part["file"]["bytes"] (A2A FilePart shape).

        Regression: the interceptor used to read part["mimeType"] /
        part["data"], which don't exist on A2A file parts, so every upload
        became "[Unsupported file type: ]".
        """
        import base64

        payload = base64.b64encode(b"hello from a text file").decode()
        messages = [
            cast(
                Message,
                {
                    "role": "user",
                    "parts": [
                        {
                            "kind": "file",
                            "file": {
                                "bytes": payload,
                                "mimeType": "text/plain",
                                "name": "notes.txt",
                            },
                        }
                    ],
                },
            )
        ]

        result = MessageConverter.to_chat_format(messages)

        assert len(result) == 1
        assert "hello from a text file" in result[0]["content"]
        assert "Unsupported file type" not in result[0]["content"]

    def test_to_chat_format_marks_unsupported_file_types(self):
        """Unsupported MIME types report the actual type, not an empty string."""
        messages = [
            cast(
                Message,
                {
                    "role": "user",
                    "parts": [
                        {
                            "kind": "file",
                            "file": {
                                "bytes": "aWdub3JlZA==",
                                "mimeType": "image/png",
                                "name": "photo.png",
                            },
                        }
                    ],
                },
            )
        ]

        result = MessageConverter.to_chat_format(messages)

        assert len(result) == 1
        assert "[Unsupported file type: image/png]" in result[0]["content"]
