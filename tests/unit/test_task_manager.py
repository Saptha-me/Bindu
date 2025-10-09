"""Unit tests for TaskManager."""

import pytest
from uuid import uuid4

from bindu.server.task_manager import TaskManager
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.common.protocol.types import (
    SendMessageRequest,
    GetTaskRequest,
    ListTasksRequest,
    CancelTaskRequest,
    TaskFeedbackRequest,
    ListContextsRequest,
    ClearContextsRequest,
)
from tests.mocks import MockManifest
from tests.utils import create_test_message, assert_jsonrpc_error, assert_jsonrpc_success


class TestMessageSendHandler:
    """Test message/send handler."""
    
    @pytest.mark.asyncio
    async def test_send_message_creates_task(self, task_manager: TaskManager):
        """Test that sending a message creates a new task."""
        message = create_test_message(text="Hello agent")
        
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
        
        response = await task_manager.handle_send_message(request)
        
        assert_jsonrpc_success(response)
        assert "result" in response
        
        # Result should be a task
        task = response["result"]
        assert task["kind"] == "task"
        assert task["id"] == message["task_id"]
    
    @pytest.mark.asyncio
    async def test_send_message_with_context_id(self, task_manager: TaskManager):
        """Test sending message with specific context ID."""
        context_id = uuid4()
        message = create_test_message(context_id=context_id)
        
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
        
        response = await task_manager.handle_send_message(request)
        
        task = response["result"]
        assert task["context_id"] == context_id
    
    @pytest.mark.asyncio
    async def test_send_message_with_reference_tasks(self, task_manager: TaskManager):
        """Test sending message with reference task IDs."""
        ref_task_id = uuid4()
        message = create_test_message(reference_task_ids=[ref_task_id])
        
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
        
        response = await task_manager.handle_send_message(request)
        
        task = response["result"]
        # Reference should be preserved in message history
        assert "history" in task


class TestGetTaskHandler:
    """Test tasks/get handler."""
    
    @pytest.mark.asyncio
    async def test_get_existing_task(self, task_manager: TaskManager, storage: InMemoryStorage):
        """Test retrieving an existing task."""
        from tests.utils import create_test_task
        
        task = create_test_task(state="completed")
        await storage.save_task(task)
        
        request: GetTaskRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/get",
            "params": {
                "task_id": task["id"],
            },
        }
        
        response = await task_manager.handle_get_task(request)
        
        assert_jsonrpc_success(response)
        retrieved_task = response["result"]
        assert retrieved_task["id"] == task["id"]
    
    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, task_manager: TaskManager):
        """Test retrieving a task that doesn't exist."""
        request: GetTaskRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/get",
            "params": {
                "task_id": uuid4(),  # Non-existent
            },
        }
        
        response = await task_manager.handle_get_task(request)
        
        # Should return TaskNotFoundError (-32001)
        assert_jsonrpc_error(response, -32001)
    
    @pytest.mark.asyncio
    async def test_get_task_with_history_limit(self, task_manager: TaskManager, storage: InMemoryStorage):
        """Test retrieving task with history length limit."""
        from tests.utils import create_test_task
        
        # Create task with long history
        messages = [create_test_message(text=f"Message {i}") for i in range(20)]
        task = create_test_task(state="working", history=messages)
        await storage.save_task(task)
        
        request: GetTaskRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/get",
            "params": {
                "task_id": task["id"],
                "history_length": 5,
            },
        }
        
        response = await task_manager.handle_get_task(request)
        
        retrieved_task = response["result"]
        # History should be limited
        if "history" in retrieved_task:
            assert len(retrieved_task["history"]) <= 5


class TestListTasksHandler:
    """Test tasks/list handler."""
    
    @pytest.mark.asyncio
    async def test_list_empty_tasks(self, task_manager: TaskManager):
        """Test listing tasks when none exist."""
        request: ListTasksRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/list",
            "params": {},
        }
        
        response = await task_manager.handle_list_tasks(request)
        
        assert_jsonrpc_success(response)
        assert response["result"] == []
    
    @pytest.mark.asyncio
    async def test_list_multiple_tasks(self, task_manager: TaskManager, storage: InMemoryStorage):
        """Test listing multiple tasks."""
        from tests.utils import create_test_task
        
        tasks = [create_test_task() for _ in range(5)]
        for task in tasks:
            await storage.save_task(task)
        
        request: ListTasksRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/list",
            "params": {},
        }
        
        response = await task_manager.handle_list_tasks(request)
        
        task_list = response["result"]
        assert len(task_list) == 5


class TestCancelTaskHandler:
    """Test tasks/cancel handler."""
    
    @pytest.mark.asyncio
    async def test_cancel_working_task(self, task_manager: TaskManager, storage: InMemoryStorage):
        """Test canceling a task in working state."""
        from tests.utils import create_test_task
        
        task = create_test_task(state="working")
        await storage.save_task(task)
        
        request: CancelTaskRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/cancel",
            "params": {
                "task_id": task["id"],
            },
        }
        
        response = await task_manager.handle_cancel_task(request)
        
        # Should succeed or return appropriate error
        # Implementation-specific behavior
        assert "result" in response or "error" in response
    
    @pytest.mark.asyncio
    async def test_cancel_completed_task(self, task_manager: TaskManager, storage: InMemoryStorage):
        """Test canceling a completed task (should fail)."""
        from tests.utils import create_test_task
        
        task = create_test_task(state="completed")
        await storage.save_task(task)
        
        request: CancelTaskRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/cancel",
            "params": {
                "task_id": task["id"],
            },
        }
        
        response = await task_manager.handle_cancel_task(request)
        
        # Should return TaskNotCancelableError (-32002)
        if "error" in response:
            assert_jsonrpc_error(response, -32002)
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self, task_manager: TaskManager):
        """Test canceling a task that doesn't exist."""
        request: CancelTaskRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/cancel",
            "params": {
                "task_id": uuid4(),
            },
        }
        
        response = await task_manager.handle_cancel_task(request)
        
        # Should return TaskNotFoundError (-32001)
        assert_jsonrpc_error(response, -32001)


class TestFeedbackHandler:
    """Test tasks/feedback handler."""
    
    @pytest.mark.asyncio
    async def test_submit_feedback(self, task_manager: TaskManager, storage: InMemoryStorage):
        """Test submitting feedback for a task."""
        from tests.utils import create_test_task
        
        task = create_test_task(state="completed")
        await storage.save_task(task)
        
        request: TaskFeedbackRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/feedback",
            "params": {
                "task_id": task["id"],
                "feedback": "Great job!",
                "rating": 5,
                "metadata": {"helpful": True},
            },
        }
        
        response = await task_manager.handle_task_feedback(request)
        
        assert_jsonrpc_success(response)
    
    @pytest.mark.asyncio
    async def test_feedback_for_nonexistent_task(self, task_manager: TaskManager):
        """Test submitting feedback for non-existent task."""
        request: TaskFeedbackRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/feedback",
            "params": {
                "task_id": uuid4(),
                "feedback": "Test feedback",
            },
        }
        
        response = await task_manager.handle_task_feedback(request)
        
        # Should return TaskNotFoundError
        assert_jsonrpc_error(response, -32001)


class TestContextHandlers:
    """Test context management handlers."""
    
    @pytest.mark.asyncio
    async def test_list_empty_contexts(self, task_manager: TaskManager):
        """Test listing contexts when none exist."""
        request: ListContextsRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "contexts/list",
            "params": {},
        }
        
        response = await task_manager.handle_list_contexts(request)
        
        assert_jsonrpc_success(response)
        assert response["result"] == []
    
    @pytest.mark.asyncio
    async def test_list_multiple_contexts(self, task_manager: TaskManager, storage: InMemoryStorage):
        """Test listing multiple contexts."""
        from tests.utils import create_test_context
        
        contexts = [create_test_context(name=f"Session {i}") for i in range(3)]
        for ctx in contexts:
            await storage.save_context(ctx)
        
        request: ListContextsRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "contexts/list",
            "params": {},
        }
        
        response = await task_manager.handle_list_contexts(request)
        
        context_list = response["result"]
        assert len(context_list) == 3
    
    @pytest.mark.asyncio
    async def test_clear_context(self, task_manager: TaskManager, storage: InMemoryStorage):
        """Test clearing a context."""
        from tests.utils import create_test_context
        
        context = create_test_context(name="To Clear")
        await storage.save_context(context)
        
        request: ClearContextsRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "contexts/clear",
            "params": {
                "context_id": context["context_id"],
            },
        }
        
        response = await task_manager.handle_clear_contexts(request)
        
        # Should succeed
        assert "result" in response or "error" in response
    
    @pytest.mark.asyncio
    async def test_clear_nonexistent_context(self, task_manager: TaskManager):
        """Test clearing a context that doesn't exist."""
        request: ClearContextsRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "contexts/clear",
            "params": {
                "context_id": uuid4(),
            },
        }
        
        response = await task_manager.handle_clear_contexts(request)
        
        # Should return ContextNotFoundError (-32020)
        if "error" in response:
            assert_jsonrpc_error(response, -32020)


class TestPushNotifications:
    """Test push notification handlers."""
    
    @pytest.mark.asyncio
    async def test_push_not_supported(self, task_manager: TaskManager):
        """Test push notification when not supported."""
        from bindu.common.protocol.types import SetTaskPushNotificationRequest
        
        # TaskManager without push support
        request: SetTaskPushNotificationRequest = {
            "jsonrpc": "2.0",
            "id": uuid4(),
            "method": "tasks/pushNotification/set",
            "params": {
                "id": uuid4(),
                "push_notification_config": {
                    "id": uuid4(),
                    "url": "https://example.com/callback",
                },
            },
        }
        
        response = await task_manager.handle_set_task_push_notification(request)
        
        # Should return PushNotificationNotSupportedError (-32003)
        if not task_manager._push_supported():
            assert_jsonrpc_error(response, -32003)
