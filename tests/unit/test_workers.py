import datetime
import uuid

import anyio
import pytest

from bindu.server.workers.base import Worker


class SimpleStorage:
    def __init__(self, task):
        self.task = task
        self.last_update = None

    async def load_task(self, task_id, history_length=None):
        if self.task["id"] == task_id:
            return self.task
        return None

    async def update_task(self, task_id, state, new_artifacts=None, new_messages=None, metadata=None):
        self.task["status"]["state"] = state
        self.task["status"]["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"
        if metadata is not None:
            self.task["metadata"] = metadata
        self.last_update = {"state": state, "metadata": metadata}
        return self.task


class TestWorker(Worker):
    async def run_task(self, params):
        pass

    async def cancel_task(self, params):
        pass

    def build_message_history(self, history):
        return []

    def build_artifacts(self, result):
        return []

    async def capture_execution_state(self, task_id):
        await anyio.sleep(0)
        return {"cursor": 123}

    async def restore_execution_state(self, task_id, checkpoint):
        # record restore call
        self._restored = checkpoint


@pytest.mark.anyio
async def test_pause_resume_cycle():
    tid = uuid.uuid4()
    ctx = uuid.uuid4()
    task = {
        "id": tid,
        "context_id": ctx,
        "kind": "task",
        "status": {"state": "working", "timestamp": "2026-05-01T00:00:00Z"},
        "metadata": {},
    }

    storage = SimpleStorage(task)
    worker = TestWorker(scheduler=None, storage=storage)

    # Pause
    await worker._handle_pause({"task_id": tid})
    assert storage.last_update["state"] == "suspended"
    assert storage.last_update["metadata"].get("suspended") is True
    assert "suspended_checkpoint" in storage.last_update["metadata"]

    # Resume
    await worker._handle_resume({"task_id": tid})
    assert storage.last_update["state"] == "resumed"
    assert storage.last_update["metadata"].get("suspended") is None
    assert "resumed_at" in storage.last_update["metadata"]
