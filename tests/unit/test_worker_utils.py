"""Unit tests for worker utilities."""

from uuid import uuid4

import pytest

from bindu.utils.worker_utils import (
    ArtifactBuilder,
    MessageConverter,
    PartConverter,
    TaskStateManager,
)


class TestMessageConverter:
    """Test MessageConverter class."""

    def test_to_chat_format_basic(self):
        """Test converting protocol messages to chat format."""
        history = [
            {"role": "user", "parts": [{"kind": "text", "text": "Hello"}]},
            {"role": "agent", "parts": [{"kind": "text", "text": "Hi there"}]},
        ]

        result = MessageConverter.to_chat_format(history)

        assert len(result) == 2
        assert result[0]["role"] == "user"
        assert result[0]["content"] == "Hello"
        assert result[1]["role"] == "assistant"
        assert result[1]["content"] == "Hi there"

    def test_to_chat_format_multiple_text_parts(self):
        """Test converting messages with multiple text parts."""
        history = [
            {
                "role": "user",
                "parts": [
                    {"kind": "text", "text": "Hello"},
                    {"kind": "text", "text": "World"},
                ],
            },
        ]

        result = MessageConverter.to_chat_format(history)

        assert len(result) == 1
        assert "Hello" in result[0]["content"]
        assert "World" in result[0]["content"]

    def test_to_chat_format_empty_history(self):
        """Test converting empty history."""
        result = MessageConverter.to_chat_format([])
        assert result == []

    def test_to_protocol_messages_string_result(self):
        """Test converting string result to protocol messages."""
        result = "Test response"
        task_id = uuid4()
        context_id = uuid4()

        messages = MessageConverter.to_protocol_messages(result, task_id, context_id)

        assert len(messages) == 1
        assert messages[0]["role"] == "assistant"
        assert messages[0]["task_id"] == task_id
        assert messages[0]["context_id"] == context_id
        assert len(messages[0]["parts"]) > 0

    def test_to_protocol_messages_without_ids(self):
        """Test converting result without task/context IDs."""
        result = "Test response"

        messages = MessageConverter.to_protocol_messages(result)

        assert len(messages) == 1
        assert "task_id" not in messages[0]
        assert "context_id" not in messages[0]


class TestPartConverter:
    """Test PartConverter class."""

    def test_dict_to_part_text(self):
        """Test converting dict to TextPart."""
        data = {"kind": "text", "text": "Hello"}

        part = PartConverter.dict_to_part(data)

        assert part["kind"] == "text"
        assert part["text"] == "Hello"

    def test_dict_to_part_file(self):
        """Test converting dict to FilePart."""
        data = {"kind": "file", "file": "test.txt"}

        part = PartConverter.dict_to_part(data)

        assert part["kind"] == "file"
        assert part["file"] == "test.txt"

    def test_dict_to_part_data(self):
        """Test converting dict to DataPart."""
        data = {"kind": "data", "data": {"key": "value"}}

        part = PartConverter.dict_to_part(data)

        assert part["kind"] == "data"
        assert part["data"]["key"] == "value"

    def test_dict_to_part_unknown(self):
        """Test converting unknown dict to DataPart."""
        data = {"unknown": "field"}

        part = PartConverter.dict_to_part(data)

        assert part["kind"] == "data"

    def test_result_to_parts_string(self):
        """Test converting string result to parts."""
        result = "Hello, world!"

        parts = PartConverter.result_to_parts(result)

        assert len(parts) == 1
        assert parts[0]["kind"] == "text"
        assert parts[0]["text"] == "Hello, world!"

    def test_result_to_parts_list_of_strings(self):
        """Test converting list of strings to parts."""
        result = ["Hello", "World"]

        parts = PartConverter.result_to_parts(result)

        assert len(parts) == 2
        assert all(p["kind"] == "text" for p in parts)

    def test_result_to_parts_dict(self):
        """Test converting dict result to parts."""
        result = {"kind": "text", "text": "Hello"}

        parts = PartConverter.result_to_parts(result)

        assert len(parts) == 1
        assert parts[0]["kind"] == "text"

    def test_result_to_parts_mixed_list(self):
        """Test converting mixed list to parts."""
        result = ["text", {"kind": "data", "data": {}}, 123]

        parts = PartConverter.result_to_parts(result)

        assert len(parts) == 3

    def test_result_to_parts_empty_list(self):
        """Test converting empty list to parts."""
        result = []

        parts = PartConverter.result_to_parts(result)

        assert parts == []


class TestArtifactBuilder:
    """Test ArtifactBuilder class."""

    def test_from_result_string(self):
        """Test building artifact from string result."""
        result = "Test output"

        artifacts = ArtifactBuilder.from_result(result, artifact_name="output.txt")

        assert len(artifacts) == 1
        assert artifacts[0]["name"] == "output.txt"
        assert len(artifacts[0]["parts"]) > 0

    def test_from_result_list_of_strings(self):
        """Test building artifact from list of strings."""
        result = ["Line 1", "Line 2", "Line 3"]

        artifacts = ArtifactBuilder.from_result(result, artifact_name="output.txt")

        assert len(artifacts) == 1
        assert "Line 1" in str(artifacts[0]["parts"])

    def test_from_result_structured_data(self):
        """Test building artifact from structured data."""
        result = {"key": "value", "number": 42}

        artifacts = ArtifactBuilder.from_result(result, artifact_name="data.json")

        assert len(artifacts) == 1
        assert artifacts[0]["parts"][0]["kind"] == "data"

    def test_from_result_default_name(self):
        """Test building artifact with default name."""
        result = "Test"

        artifacts = ArtifactBuilder.from_result(result)

        assert artifacts[0]["name"] == "result"


class TestTaskStateManager:
    """Test TaskStateManager class."""

    @pytest.mark.asyncio
    async def test_validate_task_state_success(self):
        """Test validating task state when it matches."""
        task = {
            "task_id": str(uuid4()),
            "status": {"state": "submitted"},
        }

        # Should not raise
        await TaskStateManager.validate_task_state(task, "submitted")

    @pytest.mark.asyncio
    async def test_validate_task_state_failure(self):
        """Test validating task state when it doesn't match."""
        task = {
            "id": str(uuid4()),
            "status": {"state": "completed"},
        }

        with pytest.raises(ValueError, match="already processed"):
            await TaskStateManager.validate_task_state(task, "submitted")

    def test_build_response_messages_string(self):
        """Test building response messages from string."""
        result = "Test response"

        messages = TaskStateManager.build_response_messages(result)

        assert len(messages) == 1
        assert messages[0]["role"] == "agent"
        assert messages[0]["kind"] == "message"

    def test_build_response_messages_list(self):
        """Test building response messages from list."""
        result = ["Message 1", "Message 2"]

        messages = TaskStateManager.build_response_messages(result)

        assert len(messages) == 2
        assert all(m["role"] == "agent" for m in messages)
