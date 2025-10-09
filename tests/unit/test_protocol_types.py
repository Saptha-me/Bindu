"""Unit tests for A2A protocol type definitions and validation."""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from bindu.common.protocol.types import (
    Artifact,
    Context,
    Message,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
    FilePart,
    DataPart,
    SendMessageRequest,
    GetTaskRequest,
    a2a_request_ta,
    agent_card_ta,
)
from tests.utils import create_test_message, create_test_task, create_test_artifact, create_test_context


class TestMessageValidation:
    """Test Message type validation."""
    
    def test_create_valid_message(self):
        """Test creating a valid message."""
        message = create_test_message(text="Hello")
        
        assert message["kind"] == "message"
        assert message["role"] == "user"
        assert len(message["parts"]) == 1
        assert message["parts"][0]["kind"] == "text"
        assert message["parts"][0]["text"] == "Hello"
    
    def test_message_with_multiple_parts(self):
        """Test message with multiple parts."""
        text_part: TextPart = {"kind": "text", "text": "Hello"}
        data_part: DataPart = {"kind": "data", "data": {"key": "value"}}
        
        message: Message = {
            "message_id": uuid4(),
            "context_id": uuid4(),
            "task_id": uuid4(),
            "kind": "message",
            "parts": [text_part, data_part],
            "role": "user",
        }
        
        assert len(message["parts"]) == 2
        assert message["parts"][0]["kind"] == "text"
        assert message["parts"][1]["kind"] == "data"
    
    def test_message_with_reference_task_ids(self):
        """Test message with reference task IDs."""
        ref_task_id = uuid4()
        message = create_test_message(reference_task_ids=[ref_task_id])
        
        assert "reference_task_ids" in message
        assert message["reference_task_ids"][0] == ref_task_id
    
    def test_message_with_metadata(self):
        """Test message with metadata."""
        metadata = {"custom_field": "custom_value"}
        message = create_test_message(metadata=metadata)
        
        assert "metadata" in message
        assert message["metadata"]["custom_field"] == "custom_value"


class TestTaskValidation:
    """Test Task type validation."""
    
    def test_create_valid_task(self):
        """Test creating a valid task."""
        task = create_test_task(state="submitted")
        
        assert task["kind"] == "task"
        assert task["status"]["state"] == "submitted"
        assert "timestamp" in task["status"]
    
    def test_task_state_transitions(self):
        """Test all valid task states."""
        states: list[TaskState] = [
            "submitted",
            "working",
            "input-required",
            "auth-required",
            "completed",
            "canceled",
            "failed",
            "rejected",
        ]
        
        for state in states:
            task = create_test_task(state=state)
            assert task["status"]["state"] == state
    
    def test_task_with_artifacts(self):
        """Test task with artifacts."""
        artifact = create_test_artifact(text="Result")
        task = create_test_task(state="completed", artifacts=[artifact])
        
        assert "artifacts" in task
        assert len(task["artifacts"]) == 1
        assert task["artifacts"][0]["artifact_id"] == artifact["artifact_id"]
    
    def test_task_with_history(self):
        """Test task with message history."""
        msg1 = create_test_message(text="First")
        msg2 = create_test_message(text="Second")
        task = create_test_task(history=[msg1, msg2])
        
        assert "history" in task
        assert len(task["history"]) == 2
    
    def test_task_with_metadata(self):
        """Test task with metadata."""
        metadata = {"auth_type": "api_key", "service": "test"}
        task = create_test_task(metadata=metadata)
        
        assert "metadata" in task
        assert task["metadata"]["auth_type"] == "api_key"


class TestArtifactValidation:
    """Test Artifact type validation."""
    
    def test_create_valid_artifact(self):
        """Test creating a valid artifact."""
        artifact = create_test_artifact(name="output", text="Result")
        
        assert artifact["name"] == "output"
        assert len(artifact["parts"]) == 1
        assert artifact["parts"][0]["text"] == "Result"
    
    def test_artifact_with_multiple_parts(self):
        """Test artifact with multiple parts."""
        text_part: TextPart = {"kind": "text", "text": "Content"}
        data_part: DataPart = {"kind": "data", "data": {"result": 42}}
        
        artifact: Artifact = {
            "artifact_id": uuid4(),
            "name": "multi_part",
            "parts": [text_part, data_part],
        }
        
        assert len(artifact["parts"]) == 2
    
    def test_artifact_append_flag(self):
        """Test artifact with append flag."""
        artifact: Artifact = {
            "artifact_id": uuid4(),
            "name": "streaming",
            "parts": [{"kind": "text", "text": "chunk"}],
            "append": True,
        }
        
        assert artifact["append"] is True
    
    def test_artifact_last_chunk(self):
        """Test artifact with last_chunk flag."""
        artifact: Artifact = {
            "artifact_id": uuid4(),
            "name": "streaming",
            "parts": [{"kind": "text", "text": "final chunk"}],
            "last_chunk": True,
        }
        
        assert artifact["last_chunk"] is True


class TestContextValidation:
    """Test Context type validation."""
    
    def test_create_valid_context(self):
        """Test creating a valid context."""
        context = create_test_context(name="Test Session")
        
        assert context["kind"] == "context"
        assert context["name"] == "Test Session"
        assert "created_at" in context
        assert "updated_at" in context
    
    def test_context_with_tasks(self):
        """Test context with task IDs."""
        task_ids = [uuid4(), uuid4()]
        context = create_test_context(tasks=task_ids)
        
        assert "tasks" in context
        assert len(context["tasks"]) == 2
    
    def test_context_status_transitions(self):
        """Test context status values."""
        statuses = ["active", "paused", "completed", "archived"]
        
        for status in statuses:
            context = create_test_context(status=status)
            assert context["status"] == status
    
    def test_context_with_metadata(self):
        """Test context with metadata."""
        metadata = {"user_id": "123", "session_type": "chat"}
        context = create_test_context(metadata=metadata)
        
        assert "metadata" in context
        assert context["metadata"]["user_id"] == "123"


class TestJSONRPCRequests:
    """Test JSON-RPC request/response types."""
    
    def test_send_message_request(self):
        """Test SendMessageRequest structure."""
        message = create_test_message()
        
        request: SendMessageRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "message/send",
            "params": {
                "message": message,
                "configuration": {
                    "accepted_output_modes": ["application/json"],
                },
            },
        }
        
        assert request["method"] == "message/send"
        assert request["jsonrpc"] == "2.0"
    
    def test_get_task_request(self):
        """Test GetTaskRequest structure."""
        task_id = uuid4()
        
        request: GetTaskRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/get",
            "params": {
                "task_id": task_id,
            },
        }
        
        assert request["method"] == "tasks/get"
        assert request["params"]["task_id"] == task_id
    
    def test_a2a_request_validation(self):
        """Test A2A request type adapter validation."""
        message = create_test_message()
        
        request_dict = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "message/send",
            "params": {
                "message": message,
                "configuration": {
                    "acceptedOutputModes": ["application/json"],
                },
            },
        }
        
        # Should validate successfully
        validated = a2a_request_ta.validate_python(request_dict)
        assert validated["method"] == "message/send"


class TestPartTypes:
    """Test Part type variations."""
    
    def test_text_part(self):
        """Test TextPart creation."""
        part: TextPart = {
            "kind": "text",
            "text": "Hello world",
        }
        
        assert part["kind"] == "text"
        assert part["text"] == "Hello world"
    
    def test_text_part_with_metadata(self):
        """Test TextPart with metadata."""
        part: TextPart = {
            "kind": "text",
            "text": "Content",
            "metadata": {"language": "en"},
        }
        
        assert "metadata" in part
        assert part["metadata"]["language"] == "en"
    
    def test_file_part_with_bytes(self):
        """Test FilePart with bytes."""
        part: FilePart = {
            "kind": "file",
            "file": {
                "bytes": "base64encodedcontent",
                "mimeType": "text/plain",
                "name": "test.txt",
            },
        }
        
        assert part["kind"] == "file"
        assert part["file"]["name"] == "test.txt"
    
    def test_file_part_with_uri(self):
        """Test FilePart with URI."""
        part: FilePart = {
            "kind": "file",
            "file": {
                "bytes": "",
                "uri": "https://example.com/file.pdf",
                "mimeType": "application/pdf",
            },
        }
        
        assert part["file"]["uri"] == "https://example.com/file.pdf"
    
    def test_data_part(self):
        """Test DataPart with structured data."""
        part: DataPart = {
            "kind": "data",
            "data": {
                "result": 42,
                "status": "success",
                "items": [1, 2, 3],
            },
        }
        
        assert part["kind"] == "data"
        assert part["data"]["result"] == 42
        assert len(part["data"]["items"]) == 3


class TestErrorCodes:
    """Test JSON-RPC error code definitions."""
    
    def test_standard_error_codes(self):
        """Test standard JSON-RPC error codes."""
        from bindu.common.protocol.types import (
            JSONParseError,
            InvalidRequestError,
            MethodNotFoundError,
            InvalidParamsError,
            InternalError,
        )
        
        # These should have the correct code values
        assert JSONParseError.__annotations__["code"] == -32700
        assert InvalidRequestError.__annotations__["code"] == -32600
        assert MethodNotFoundError.__annotations__["code"] == -32601
        assert InvalidParamsError.__annotations__["code"] == -32602
        assert InternalError.__annotations__["code"] == -32603
    
    def test_a2a_error_codes(self):
        """Test A2A-specific error codes."""
        from bindu.common.protocol.types import (
            TaskNotFoundError,
            TaskNotCancelableError,
            PushNotificationNotSupportedError,
        )
        
        assert TaskNotFoundError.__annotations__["code"] == -32001
        assert TaskNotCancelableError.__annotations__["code"] == -32002
        assert PushNotificationNotSupportedError.__annotations__["code"] == -32003
    
    def test_bindu_error_codes(self):
        """Test Bindu-specific error codes."""
        from bindu.common.protocol.types import (
            TaskImmutableError,
            ContextNotFoundError,
        )
        
        assert TaskImmutableError.__annotations__["code"] == -32008
        assert ContextNotFoundError.__annotations__["code"] == -32020
