"""Unit tests for task scheduler (InMemoryScheduler)."""

import asyncio
from uuid import uuid4

import pytest

from bindu.server.scheduler.memory_scheduler import InMemoryScheduler


@pytest.mark.asyncio
async def test_scheduler_basic_flow():
    """Test scheduler can send and receive operations."""
    async with InMemoryScheduler() as scheduler:
        task_id = uuid4()
        received = []
        
        async def consumer():
            """Consume one task operation."""
            async for op in scheduler.receive_task_operations():
                received.append(op)
                return
        
        # Start consumer
        consumer_task = asyncio.create_task(consumer())
        
        # Give consumer time to start
        await asyncio.sleep(0.01)
        
        # Send task
        await scheduler.run_task({"task_id": task_id, "context_id": uuid4()})
        
        # Wait for consumer
        await asyncio.wait_for(consumer_task, timeout=1.0)
        
        assert len(received) == 1
        assert received[0]["operation"] == "run"
        assert received[0]["params"]["task_id"] == task_id


@pytest.mark.asyncio
async def test_scheduler_operations():
    """Test all scheduler operations."""
    async with InMemoryScheduler() as scheduler:
        task_id = uuid4()
        received = []
        
        async def consumer():
            """Consume operations."""
            count = 0
            async for op in scheduler.receive_task_operations():
                received.append(op)
                count += 1
                if count >= 4:
                    return
        
        # Start consumer
        consumer_task = asyncio.create_task(consumer())
        await asyncio.sleep(0.01)
        
        # Send operations
        await scheduler.run_task({"task_id": task_id, "context_id": uuid4()})
        await scheduler.cancel_task({"task_id": task_id})
        await scheduler.pause_task({"task_id": task_id})
        await scheduler.resume_task({"task_id": task_id})
        
        # Wait for consumer
        await asyncio.wait_for(consumer_task, timeout=1.0)
        
        assert len(received) == 4
        assert received[0]["operation"] == "run"
        assert received[1]["operation"] == "cancel"
        assert received[2]["operation"] == "pause"
        assert received[3]["operation"] == "resume"
