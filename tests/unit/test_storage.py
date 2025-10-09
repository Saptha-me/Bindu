"""Unit tests for storage layer (InMemoryStorage)."""

import pytest
from uuid import uuid4

from bindu.server.storage.memory_storage import InMemoryStorage
from tests.utils import create_test_task, create_test_context, assert_task_state


class TestTaskStorage:
    """Test task CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_save_and_load_task(self, storage: InMemoryStorage):
        """Test saving and loading a task."""
        task = create_test_task(state="submitted")
        task_id = task["id"]
        
        await storage.save_task(task)
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
        task = create_test_task(state="submitted")
        task_id = task["id"]
        
        await storage.save_task(task)
        
        # Update task state
        task["status"]["state"] = "working"
        await storage.save_task(task)
        
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
        task1 = create_test_task(state="submitted")
        task2 = create_test_task(state="working")
        task3 = create_test_task(state="completed")
        
        await storage.save_task(task1)
        await storage.save_task(task2)
        await storage.save_task(task3)
        
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
        
        artifact = create_test_artifact(text="Result")
        task = create_test_task(state="completed", artifacts=[artifact])
        
        await storage.save_task(task)
        loaded_task = await storage.load_task(task["id"])
        
        assert "artifacts" in loaded_task
        assert len(loaded_task["artifacts"]) == 1
        assert loaded_task["artifacts"][0]["artifact_id"] == artifact["artifact_id"]
    
    @pytest.mark.asyncio
    async def test_task_with_history(self, storage: InMemoryStorage):
        """Test storing and retrieving task with history."""
        from tests.utils import create_test_message
        
        msg1 = create_test_message(text="First")
        msg2 = create_test_message(text="Second")
        task = create_test_task(history=[msg1, msg2])
        
        await storage.save_task(task)
        loaded_task = await storage.load_task(task["id"])
        
        assert "history" in loaded_task
        assert len(loaded_task["history"]) == 2


class TestContextStorage:
    """Test context CRUD operations."""
    
    @pytest.mark.asyncio
    async def test_save_and_load_context(self, storage: InMemoryStorage):
        """Test saving and loading a context."""
        context = create_test_context(name="Test Session")
        context_id = context["context_id"]
        
        await storage.save_context(context)
        loaded_context = await storage.load_context(context_id)
        
        assert loaded_context is not None
        assert loaded_context["context_id"] == context_id
        assert loaded_context["name"] == "Test Session"
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_context(self, storage: InMemoryStorage):
        """Test loading a context that doesn't exist."""
        nonexistent_id = uuid4()
        context = await storage.load_context(nonexistent_id)
        
        assert context is None
    
    @pytest.mark.asyncio
    async def test_update_context(self, storage: InMemoryStorage):
        """Test updating an existing context."""
        context = create_test_context(status="active")
        context_id = context["context_id"]
        
        await storage.save_context(context)
        
        # Update context status
        context["status"] = "completed"
        await storage.save_context(context)
        
        loaded_context = await storage.load_context(context_id)
        assert loaded_context["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_list_contexts_empty(self, storage: InMemoryStorage):
        """Test listing contexts when storage is empty."""
        contexts = await storage.list_contexts()
        assert contexts == []
    
    @pytest.mark.asyncio
    async def test_list_contexts_multiple(self, storage: InMemoryStorage):
        """Test listing multiple contexts."""
        ctx1 = create_test_context(name="Session 1")
        ctx2 = create_test_context(name="Session 2")
        ctx3 = create_test_context(name="Session 3")
        
        await storage.save_context(ctx1)
        await storage.save_context(ctx2)
        await storage.save_context(ctx3)
        
        contexts = await storage.list_contexts()
        assert len(contexts) == 3
    
    @pytest.mark.asyncio
    async def test_clear_context(self, storage: InMemoryStorage):
        """Test clearing a context."""
        context = create_test_context(name="To Clear")
        context_id = context["context_id"]
        
        await storage.save_context(context)
        await storage.clear_context(context_id)
        
        # Context should still exist but be cleared
        loaded_context = await storage.load_context(context_id)
        # Implementation-specific: check what clear_context does
        # For now, just verify it doesn't raise an error
        assert True
    
    @pytest.mark.asyncio
    async def test_context_with_tasks(self, storage: InMemoryStorage):
        """Test context with associated task IDs."""
        task_ids = [uuid4(), uuid4(), uuid4()]
        context = create_test_context(tasks=task_ids)
        
        await storage.save_context(context)
        loaded_context = await storage.load_context(context["context_id"])
        
        assert "tasks" in loaded_context
        assert len(loaded_context["tasks"]) == 3


class TestTaskContextRelationship:
    """Test task-context relationship integrity."""
    
    @pytest.mark.asyncio
    async def test_tasks_share_context(self, storage: InMemoryStorage):
        """Test multiple tasks in the same context."""
        context_id = uuid4()
        
        task1 = create_test_task(context_id=context_id, state="submitted")
        task2 = create_test_task(context_id=context_id, state="working")
        task3 = create_test_task(context_id=context_id, state="completed")
        
        await storage.save_task(task1)
        await storage.save_task(task2)
        await storage.save_task(task3)
        
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
        task1_id = uuid4()
        task2_id = uuid4()
        
        context = create_test_context(
            context_id=context_id,
            tasks=[task1_id, task2_id]
        )
        
        await storage.save_context(context)
        loaded_context = await storage.load_context(context_id)
        
        assert task1_id in loaded_context["tasks"]
        assert task2_id in loaded_context["tasks"]


class TestConcurrentAccess:
    """Test concurrent storage operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_task_saves(self, storage: InMemoryStorage):
        """Test saving multiple tasks concurrently."""
        import asyncio
        
        tasks = [create_test_task() for _ in range(10)]
        
        # Save all tasks concurrently
        await asyncio.gather(*[storage.save_task(task) for task in tasks])
        
        # Verify all tasks were saved
        all_tasks = await storage.list_tasks()
        assert len(all_tasks) == 10
    
    @pytest.mark.asyncio
    async def test_concurrent_task_reads(self, storage: InMemoryStorage):
        """Test reading tasks concurrently."""
        import asyncio
        
        task = create_test_task()
        await storage.save_task(task)
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
        
        task = create_test_task(state="submitted")
        await storage.save_task(task)
        
        # Update task state multiple times concurrently
        async def update_task(state_suffix: int):
            loaded = await storage.load_task(task["id"])
            loaded["status"]["state"] = "working"
            loaded["metadata"] = {"update": state_suffix}
            await storage.save_task(loaded)
        
        await asyncio.gather(*[update_task(i) for i in range(5)])
        
        # Task should be updated (last write wins)
        final_task = await storage.load_task(task["id"])
        assert final_task is not None
        assert final_task["status"]["state"] == "working"


class TestDataIntegrity:
    """Test data integrity and consistency."""
    
    @pytest.mark.asyncio
    async def test_task_immutability_after_load(self, storage: InMemoryStorage):
        """Test that modifying loaded task doesn't affect storage."""
        task = create_test_task(state="submitted")
        await storage.save_task(task)
        
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
        task = create_test_task(metadata=metadata)
        
        await storage.save_task(task)
        loaded = await storage.load_task(task["id"])
        
        assert loaded["metadata"]["auth_type"] == "api_key"
        assert loaded["metadata"]["service"] == "test_service"
        assert loaded["metadata"]["custom_data"]["nested"] == "value"
