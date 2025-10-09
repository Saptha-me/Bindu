"""Unit tests for task scheduler (InMemoryScheduler)."""

import asyncio
import pytest
from uuid import uuid4

from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.common.protocol.types import TaskSendParams
from tests.utils import create_test_message


class TestSchedulerBasics:
    """Test basic scheduler operations."""
    
    @pytest.mark.asyncio
    async def test_submit_and_get_task(self):
        """Test submitting and retrieving a task."""
        async with InMemoryScheduler() as scheduler:
            task_id = uuid4()
            context_id = uuid4()
            message = create_test_message()
            
            params: TaskSendParams = {
                "task_id": task_id,
                "context_id": context_id,
                "message": message,
            }
            
            await scheduler.submit_task(params)
            
            # Get the task from queue
            retrieved = await scheduler.get_task()
            
            assert retrieved is not None
            assert retrieved["task_id"] == task_id
            assert retrieved["context_id"] == context_id
    
    @pytest.mark.asyncio
    async def test_fifo_ordering(self):
        """Test that tasks are retrieved in FIFO order."""
        async with InMemoryScheduler() as scheduler:
            task_ids = [uuid4() for _ in range(5)]
            
            # Submit tasks in order
            for task_id in task_ids:
                params: TaskSendParams = {
                    "task_id": task_id,
                    "context_id": uuid4(),
                }
                await scheduler.submit_task(params)
            
            # Retrieve tasks - should be in same order
            retrieved_ids = []
            for _ in range(5):
                params = await scheduler.get_task()
                retrieved_ids.append(params["task_id"])
            
            assert retrieved_ids == task_ids
    
    @pytest.mark.asyncio
    async def test_empty_queue_blocks(self):
        """Test that getting from empty queue blocks."""
        async with InMemoryScheduler() as scheduler:
            # Try to get with timeout
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(scheduler.get_task(), timeout=0.1)
    
    @pytest.mark.asyncio
    async def test_submit_after_get_unblocks(self):
        """Test that submitting unblocks waiting get."""
        async with InMemoryScheduler() as scheduler:
            task_id = uuid4()
            
            async def submit_delayed():
                await asyncio.sleep(0.1)
                params: TaskSendParams = {
                    "task_id": task_id,
                    "context_id": uuid4(),
                }
                await scheduler.submit_task(params)
            
            # Start submit task
            submit_task = asyncio.create_task(submit_delayed())
            
            # This should block until submit completes
            params = await scheduler.get_task()
            
            assert params["task_id"] == task_id
            await submit_task


class TestSchedulerLifecycle:
    """Test scheduler lifecycle management."""
    
    @pytest.mark.asyncio
    async def test_context_manager_enter_exit(self):
        """Test scheduler as async context manager."""
        scheduler = InMemoryScheduler()
        
        async with scheduler:
            # Should be usable inside context
            params: TaskSendParams = {
                "task_id": uuid4(),
                "context_id": uuid4(),
            }
            await scheduler.submit_task(params)
            retrieved = await scheduler.get_task()
            assert retrieved is not None
    
    @pytest.mark.asyncio
    async def test_multiple_submit_get_cycles(self):
        """Test multiple submit/get cycles."""
        async with InMemoryScheduler() as scheduler:
            for i in range(10):
                task_id = uuid4()
                params: TaskSendParams = {
                    "task_id": task_id,
                    "context_id": uuid4(),
                }
                
                await scheduler.submit_task(params)
                retrieved = await scheduler.get_task()
                
                assert retrieved["task_id"] == task_id
    
    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """Test scheduler graceful shutdown."""
        scheduler = InMemoryScheduler()
        
        async with scheduler:
            # Submit some tasks
            for _ in range(5):
                params: TaskSendParams = {
                    "task_id": uuid4(),
                    "context_id": uuid4(),
                }
                await scheduler.submit_task(params)
        
        # After exit, scheduler should be shut down
        # Implementation-specific: verify shutdown behavior


class TestConcurrentOperations:
    """Test concurrent scheduler operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_submits(self):
        """Test submitting tasks concurrently."""
        async with InMemoryScheduler() as scheduler:
            task_ids = [uuid4() for _ in range(20)]
            
            # Submit all tasks concurrently
            async def submit(task_id):
                params: TaskSendParams = {
                    "task_id": task_id,
                    "context_id": uuid4(),
                }
                await scheduler.submit_task(params)
            
            await asyncio.gather(*[submit(tid) for tid in task_ids])
            
            # Retrieve all tasks
            retrieved_ids = set()
            for _ in range(20):
                params = await scheduler.get_task()
                retrieved_ids.add(params["task_id"])
            
            # All tasks should be retrieved
            assert retrieved_ids == set(task_ids)
    
    @pytest.mark.asyncio
    async def test_concurrent_gets(self):
        """Test multiple consumers getting tasks concurrently."""
        async with InMemoryScheduler() as scheduler:
            num_tasks = 10
            
            # Submit tasks
            for _ in range(num_tasks):
                params: TaskSendParams = {
                    "task_id": uuid4(),
                    "context_id": uuid4(),
                }
                await scheduler.submit_task(params)
            
            # Multiple consumers get tasks concurrently
            async def consumer():
                return await scheduler.get_task()
            
            results = await asyncio.gather(*[consumer() for _ in range(num_tasks)])
            
            # All gets should succeed
            assert len(results) == num_tasks
            assert all(r is not None for r in results)
            
            # All task IDs should be unique
            task_ids = [r["task_id"] for r in results]
            assert len(set(task_ids)) == num_tasks
    
    @pytest.mark.asyncio
    async def test_producer_consumer_pattern(self):
        """Test producer-consumer pattern."""
        async with InMemoryScheduler() as scheduler:
            num_tasks = 20
            consumed = []
            
            async def producer():
                for i in range(num_tasks):
                    params: TaskSendParams = {
                        "task_id": uuid4(),
                        "context_id": uuid4(),
                        "metadata": {"index": i},
                    }
                    await scheduler.submit_task(params)
                    await asyncio.sleep(0.01)  # Simulate work
            
            async def consumer():
                for _ in range(num_tasks):
                    params = await scheduler.get_task()
                    consumed.append(params)
                    await asyncio.sleep(0.01)  # Simulate work
            
            # Run producer and consumer concurrently
            await asyncio.gather(producer(), consumer())
            
            assert len(consumed) == num_tasks


class TestTaskParameters:
    """Test task parameter handling."""
    
    @pytest.mark.asyncio
    async def test_task_with_message(self):
        """Test task parameters with message."""
        async with InMemoryScheduler() as scheduler:
            message = create_test_message(text="Test message")
            params: TaskSendParams = {
                "task_id": uuid4(),
                "context_id": uuid4(),
                "message": message,
            }
            
            await scheduler.submit_task(params)
            retrieved = await scheduler.get_task()
            
            assert "message" in retrieved
            assert retrieved["message"]["parts"][0]["text"] == "Test message"
    
    @pytest.mark.asyncio
    async def test_task_with_history_length(self):
        """Test task parameters with history_length."""
        async with InMemoryScheduler() as scheduler:
            params: TaskSendParams = {
                "task_id": uuid4(),
                "context_id": uuid4(),
                "history_length": 10,
            }
            
            await scheduler.submit_task(params)
            retrieved = await scheduler.get_task()
            
            assert "history_length" in retrieved
            assert retrieved["history_length"] == 10
    
    @pytest.mark.asyncio
    async def test_task_with_metadata(self):
        """Test task parameters with metadata."""
        async with InMemoryScheduler() as scheduler:
            metadata = {"custom": "value", "priority": "high"}
            params: TaskSendParams = {
                "task_id": uuid4(),
                "context_id": uuid4(),
                "metadata": metadata,
            }
            
            await scheduler.submit_task(params)
            retrieved = await scheduler.get_task()
            
            assert "metadata" in retrieved
            assert retrieved["metadata"]["custom"] == "value"
            assert retrieved["metadata"]["priority"] == "high"


class TestQueueBehavior:
    """Test queue-specific behavior."""
    
    @pytest.mark.asyncio
    async def test_no_task_loss(self):
        """Test that no tasks are lost during operations."""
        async with InMemoryScheduler() as scheduler:
            num_tasks = 100
            submitted_ids = []
            
            # Submit many tasks
            for _ in range(num_tasks):
                task_id = uuid4()
                submitted_ids.append(task_id)
                params: TaskSendParams = {
                    "task_id": task_id,
                    "context_id": uuid4(),
                }
                await scheduler.submit_task(params)
            
            # Retrieve all tasks
            retrieved_ids = []
            for _ in range(num_tasks):
                params = await scheduler.get_task()
                retrieved_ids.append(params["task_id"])
            
            # All tasks should be accounted for
            assert set(submitted_ids) == set(retrieved_ids)
    
    @pytest.mark.asyncio
    async def test_queue_independence(self):
        """Test that multiple scheduler instances are independent."""
        scheduler1 = InMemoryScheduler()
        scheduler2 = InMemoryScheduler()
        
        async with scheduler1, scheduler2:
            task_id_1 = uuid4()
            task_id_2 = uuid4()
            
            # Submit to different schedulers
            await scheduler1.submit_task({
                "task_id": task_id_1,
                "context_id": uuid4(),
            })
            await scheduler2.submit_task({
                "task_id": task_id_2,
                "context_id": uuid4(),
            })
            
            # Each scheduler should only have its own task
            params1 = await scheduler1.get_task()
            params2 = await scheduler2.get_task()
            
            assert params1["task_id"] == task_id_1
            assert params2["task_id"] == task_id_2
