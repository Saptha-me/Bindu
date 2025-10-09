"""Unit tests for storage layer (InMemoryStorage)."""

import pytest
from uuid import uuid4

from bindu.server.storage.memory_storage import InMemoryStorage
from tests.utils import create_test_task, create_test_context, create_test_message, assert_task_state


class TestTaskStorage:
    """Test task CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_save_and_load_task(self, storage: InMemoryStorage):
        """Test saving and loading a task."""
        # Create a message to submit a task
        message = create_test_message(text="Test task")
        context_id = message["context_id"]
        
        # Submit task through storage API
        task = await storage.submit_task(context_id, message)
        task_id = task["id"]
        
        loaded_task = await storage.load_task(task_id)
        
        assert loaded_task is not None
        assert loaded_task["id"] == task_id
        assert_task_state(loaded_task, "submitted")
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_task(self, storage: InMemoryStorage):
        """Test loading a task that doesn't exist."""
        nonexistent_id = uuid4()
        task = await storage.load_task(nonexistent_id)
        
        assert task is None
    
    @pytest.mark.asyncio
    async def test_update_task(self, storage: InMemoryStorage):
        """Test updating an existing task."""
        # Submit a task first
        message = create_test_message(text="Test task")
        context_id = message["context_id"]
        task = await storage.submit_task(context_id, message)
        task_id = task["id"]
        
        # Update task state using storage API
        await storage.update_task(task_id, "working")
        
        loaded_task = await storage.load_task(task_id)
        assert_task_state(loaded_task, "working")
    
    @pytest.mark.asyncio
    async def test_list_tasks_empty(self, storage: InMemoryStorage):
        """Test listing tasks when storage is empty."""
        tasks = await storage.list_tasks()
        assert tasks == []
    
    @pytest.mark.asyncio
    async def test_list_tasks_multiple(self, storage: InMemoryStorage):
        """Test listing multiple tasks."""
        # Submit multiple tasks
        msg1 = create_test_message(text="Task 1")
        msg2 = create_test_message(text="Task 2")
        msg3 = create_test_message(text="Task 3")
        
        task1 = await storage.submit_task(msg1["context_id"], msg1)
        task2 = await storage.submit_task(msg2["context_id"], msg2)
        task3 = await storage.submit_task(msg3["context_id"], msg3)
        
        # Update states
        await storage.update_task(task2["id"], "working")
        await storage.update_task(task3["id"], "completed")
        
        tasks = await storage.list_tasks()
        assert len(tasks) == 3
        
        task_ids = {t["id"] for t in tasks}
        assert task1["id"] in task_ids
        assert task2["id"] in task_ids
        assert task3["id"] in task_ids
    
    @pytest.mark.asyncio
    async def test_task_with_artifacts(self, storage: InMemoryStorage):
        """Test storing and retrieving task with artifacts."""
        from tests.utils import create_test_artifact
        
        # Submit task
        message = create_test_message(text="Generate result")
        task = await storage.submit_task(message["context_id"], message)
        
        # Update with artifacts
        artifact = create_test_artifact(text="Result")
        await storage.update_task(task["id"], "completed", new_artifacts=[artifact])
        
        loaded_task = await storage.load_task(task["id"])
        
        assert "artifacts" in loaded_task
        assert len(loaded_task["artifacts"]) == 1
        assert loaded_task["artifacts"][0]["artifact_id"] == artifact["artifact_id"]
    
    @pytest.mark.asyncio
    async def test_task_with_history(self, storage: InMemoryStorage):
        """Test storing and retrieving task with history."""
        from tests.utils import create_test_message
        
        # Submit task with initial message
        msg1 = create_test_message(text="First")
        task = await storage.submit_task(msg1["context_id"], msg1)
        
        # Add more messages to history
        msg2 = create_test_message(text="Second", task_id=task["id"], context_id=task["context_id"])
        await storage.update_task(task["id"], "working", new_messages=[msg2])
        
        loaded_task = await storage.load_task(task["id"])
        
        assert "history" in loaded_task
        assert len(loaded_task["history"]) == 2


class TestContextStorage:
    """Test context CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_save_and_load_context(self, storage: InMemoryStorage):
        """Test saving and loading a context."""
        from uuid import uuid4
        
        context_id = uuid4()
        
        # Submit a task to create the context
        message = create_test_message(context_id=context_id, text="Test Session")
        await storage.submit_task(context_id, message)
        
        # Load context (returns list of task IDs)
        loaded_context = await storage.load_context(context_id)
        
        assert loaded_context is not None
        assert len(loaded_context) == 1
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_context(self, storage: InMemoryStorage):
        """Test loading a context that doesn't exist."""
        nonexistent_id = uuid4()
        context = await storage.load_context(nonexistent_id)
        
        assert context is None
    
    @pytest.mark.asyncio
    async def test_update_context(self, storage: InMemoryStorage):
        """Test updating an existing context."""
        from uuid import uuid4
        
        context_id = uuid4()
        
        # Create context by submitting a task
        message = create_test_message(context_id=context_id, text="Initial")
        await storage.submit_task(context_id, message)
        
        # Add another task to the context
        message2 = create_test_message(context_id=context_id, text="Second")
        await storage.submit_task(context_id, message2)
        
        # Verify context has both tasks
        loaded_context = await storage.load_context(context_id)
        assert len(loaded_context) == 2
    
    @pytest.mark.asyncio
    async def test_list_contexts_empty(self, storage: InMemoryStorage):
        """Test listing contexts when storage is empty."""
        contexts = await storage.list_contexts()
        assert contexts == []
    
    @pytest.mark.asyncio
    async def test_list_contexts_multiple(self, storage: InMemoryStorage):
        """Test listing multiple contexts."""
        from uuid import uuid4
        
        # Create multiple contexts by submitting tasks
        ctx1_id = uuid4()
        ctx2_id = uuid4()
        ctx3_id = uuid4()
        
        await storage.submit_task(ctx1_id, create_test_message(context_id=ctx1_id, text="Session 1"))
        await storage.submit_task(ctx2_id, create_test_message(context_id=ctx2_id, text="Session 2"))
        await storage.submit_task(ctx3_id, create_test_message(context_id=ctx3_id, text="Session 3"))
        
        contexts = await storage.list_contexts()
        assert len(contexts) == 3
    
    @pytest.mark.asyncio
    async def test_clear_context(self, storage: InMemoryStorage):
        """Test clearing a context."""
        from uuid import uuid4
        
        context_id = uuid4()
        
        # Create context with tasks
        await storage.submit_task(context_id, create_test_message(context_id=context_id, text="Task 1"))
        await storage.submit_task(context_id, create_test_message(context_id=context_id, text="Task 2"))
        
        # Clear the context
        await storage.clear_context(context_id)
        
        # Context should be removed
        loaded_context = await storage.load_context(context_id)
        assert loaded_context is None
    
    @pytest.mark.asyncio
    async def test_context_with_tasks(self, storage: InMemoryStorage):
        """Test context with associated task IDs."""
        context_id = uuid4()
        
        # Submit multiple tasks to the same context
        await storage.submit_task(context_id, create_test_message(context_id=context_id, text="Task 1"))
        await storage.submit_task(context_id, create_test_message(context_id=context_id, text="Task 2"))
        await storage.submit_task(context_id, create_test_message(context_id=context_id, text="Task 3"))
        
        loaded_context = await storage.load_context(context_id)
        
        assert loaded_context is not None
        assert len(loaded_context) == 3


class TestTaskContextRelationship:
    """Test task-context relationship integrity."""
    
    @pytest.mark.asyncio
    async def test_tasks_share_context(self, storage: InMemoryStorage):
        """Test multiple tasks in the same context."""
        context_id = uuid4()
        
        # Submit tasks to the same context
        task1 = await storage.submit_task(context_id, create_test_message(context_id=context_id, text="Task 1"))
        task2 = await storage.submit_task(context_id, create_test_message(context_id=context_id, text="Task 2"))
        task3 = await storage.submit_task(context_id, create_test_message(context_id=context_id, text="Task 3"))
        
        # Update states
        await storage.update_task(task2["id"], "working")
        await storage.update_task(task3["id"], "completed")
        
        # All tasks should have the same context_id
        loaded1 = await storage.load_task(task1["id"])
        loaded2 = await storage.load_task(task2["id"])
        loaded3 = await storage.load_task(task3["id"])
        
        assert loaded1["context_id"] == context_id
        assert loaded2["context_id"] == context_id
        assert loaded3["context_id"] == context_id
    
    @pytest.mark.asyncio
    async def test_context_tracks_tasks(self, storage: InMemoryStorage):
        """Test that context can track its tasks."""
        context_id = uuid4()
        
        # Submit tasks to create context
        task1 = await storage.submit_task(context_id, create_test_message(context_id=context_id, text="Task 1"))
        task2 = await storage.submit_task(context_id, create_test_message(context_id=context_id, text="Task 2"))
        
        loaded_context = await storage.load_context(context_id)
        
        assert task1["id"] in loaded_context
        assert task2["id"] in loaded_context


class TestConcurrentAccess:
    """Test concurrent storage operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_task_saves(self, storage: InMemoryStorage):
        """Test saving multiple tasks concurrently."""
        import asyncio
        
        # Create messages for tasks
        messages = [create_test_message(text=f"Task {i}") for i in range(10)]
        
        # Submit all tasks concurrently
        await asyncio.gather(*[
            storage.submit_task(msg["context_id"], msg) for msg in messages
        ])
        
        # Verify all tasks were saved
        all_tasks = await storage.list_tasks()
        assert len(all_tasks) == 10
    
    @pytest.mark.asyncio
    async def test_concurrent_task_reads(self, storage: InMemoryStorage):
        """Test reading tasks concurrently."""
        import asyncio
        
        message = create_test_message(text="Test task")
        task = await storage.submit_task(message["context_id"], message)
        task_id = task["id"]
        
        # Read the same task multiple times concurrently
        results = await asyncio.gather(*[
            storage.load_task(task_id) for _ in range(10)
        ])
        
        # All reads should succeed
        assert all(r is not None for r in results)
        assert all(r["id"] == task_id for r in results)
    
    @pytest.mark.asyncio
    async def test_concurrent_updates(self, storage: InMemoryStorage):
        """Test concurrent updates to the same task."""
        import asyncio
        
        message = create_test_message(text="Test task")
        task = await storage.submit_task(message["context_id"], message)
        
        # Update task state multiple times concurrently
        async def update_task_state(state_suffix: int):
            await storage.update_task(
                task["id"], 
                "working", 
                metadata={"update": state_suffix}
            )
        
        await asyncio.gather(*[update_task_state(i) for i in range(5)])
        
        # Task should be updated (last write wins)
        final_task = await storage.load_task(task["id"])
        assert final_task is not None
        assert final_task["status"]["state"] == "working"


class TestDataIntegrity:
    """Test data integrity and consistency."""
    
    @pytest.mark.asyncio
    async def test_task_immutability_after_load(self, storage: InMemoryStorage):
        """Test that modifying loaded task doesn't affect storage."""
        message = create_test_message(text="Test task")
        task = await storage.submit_task(message["context_id"], message)
        
        # Load and modify
        loaded = await storage.load_task(task["id"])
        loaded["status"]["state"] = "working"
        
        # Original should be unchanged in storage
        reloaded = await storage.load_task(task["id"])
        assert_task_state(reloaded, "submitted")
    
    @pytest.mark.asyncio
    async def test_metadata_preservation(self, storage: InMemoryStorage):
        """Test that metadata is preserved correctly."""
        metadata = {
            "auth_type": "api_key",
            "service": "test_service",
            "custom_data": {"nested": "value"}
        }
        
        message = create_test_message(text="Test task")
        task = await storage.submit_task(message["context_id"], message)
        
        # Update with metadata
        await storage.update_task(task["id"], "working", metadata=metadata)
        
        loaded = await storage.load_task(task["id"])
        
        assert loaded["metadata"]["auth_type"] == "api_key"
        assert loaded["metadata"]["service"] == "test_service"
        assert loaded["metadata"]["custom_data"]["nested"] == "value"
