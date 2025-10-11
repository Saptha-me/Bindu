"""Unit tests for ManifestWorker and hybrid agent pattern."""

from typing import cast
from uuid import uuid4

import pytest

from bindu.common.models import AgentManifest
from bindu.common.protocol.types import TaskSendParams
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.workers.manifest_worker import ManifestWorker
from tests.mocks import MockAgent, MockManifest
from tests.utils import assert_task_state, create_test_message


class TestNormalCompletionFlow:
    """Test normal task completion with artifacts."""

    @pytest.mark.asyncio
    async def test_agent_completes_successfully(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test agent completing task with artifact."""
        # Create mock agent that returns normal response
        agent = MockAgent(response="This is the result")
        manifest = MockManifest(agent_fn=agent)

        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        # Create task via submit_task
        message = create_test_message(text="Do something")
        task = await storage.submit_task(message["context_id"], message)

        # Run task
        params = cast(
            TaskSendParams,
            {
                "task_id": task["id"],
                "context_id": task["context_id"],
                "message": message,
            },
        )

        await worker.run_task(params)

        # Verify task completed
        completed_task = await storage.load_task(task["id"])
        assert_task_state(completed_task, "completed")

        # Verify artifact was created
        assert "artifacts" in completed_task
        assert len(completed_task["artifacts"]) > 0

    @pytest.mark.asyncio
    async def test_agent_response_in_artifact(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test that agent response is stored in artifact."""
        agent = MockAgent(response="Expected result text")
        manifest = MockManifest(agent_fn=agent)

        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)

        params = cast(
            TaskSendParams,
            {
                "task_id": task["id"],
                "context_id": task["context_id"],
                "message": message,
            },
        )

        await worker.run_task(params)

        completed_task = await storage.load_task(task["id"])
        artifact = completed_task["artifacts"][0]

        # Check artifact contains response
        assert any(
            part.get("text") == "Expected result text"
            for part in artifact["parts"]
            if part["kind"] == "text"
        )


class TestInputRequiredFlow:
    """Test input-required state handling."""

    @pytest.mark.asyncio
    async def test_agent_requires_input_structured(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test agent returning structured input-required response."""
        agent = MockAgent(response="What is your name?", response_type="input-required")
        manifest = MockManifest(agent_fn=agent)

        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Help me")
        task = await storage.submit_task(message["context_id"], message)

        params = cast(
            TaskSendParams,
            {
                "task_id": task["id"],
                "context_id": task["context_id"],
                "message": message,
            },
        )

        await worker.run_task(params)

        # Verify task is in input-required state
        updated_task = await storage.load_task(task["id"])
        assert_task_state(updated_task, "input-required")

    @pytest.mark.asyncio
    async def test_input_required_no_artifact(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test that input-required tasks don't generate artifacts."""
        agent = MockAgent(
            response="Please provide details", response_type="input-required"
        )
        manifest = MockManifest(agent_fn=agent)

        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)

        params = cast(
            TaskSendParams,
            {
                "task_id": task["id"],
                "context_id": task["context_id"],
                "message": message,
            },
        )

        await worker.run_task(params)

        updated_task = await storage.load_task(task["id"])

        # Should have message but no artifacts
        assert (
            "artifacts" not in updated_task
            or len(updated_task.get("artifacts", [])) == 0
        )

    @pytest.mark.asyncio
    async def test_input_required_message_in_status(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test that input-required prompt is in status message."""
        agent = MockAgent(
            response="What is your email?", response_type="input-required"
        )
        manifest = MockManifest(agent_fn=agent)

        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)

        params = cast(
            TaskSendParams,
            {
                "task_id": task["id"],
                "context_id": task["context_id"],
                "message": message,
            },
        )

        await worker.run_task(params)

        updated_task = await storage.load_task(task["id"])

        # Task should be in input-required state
        assert_task_state(updated_task, "input-required")

        # The prompt should be in the message history (last agent message)
        assert len(updated_task["history"]) > 1
        last_message = updated_task["history"][-1]
        assert last_message["role"] in ["agent", "assistant"]  # Accept both roles


class TestAuthRequiredFlow:
    """Test auth-required state handling."""

    @pytest.mark.asyncio
    async def test_agent_requires_auth_structured(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test agent returning structured auth-required response."""
        agent = MockAgent(
            response="Please provide API key", response_type="auth-required"
        )
        manifest = MockManifest(agent_fn=agent)

        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Access API")
        task = await storage.submit_task(message["context_id"], message)

        params = cast(
            TaskSendParams,
            {
                "task_id": task["id"],
                "context_id": task["context_id"],
                "message": message,
            },
        )

        await worker.run_task(params)

        # Verify task is in auth-required state
        updated_task = await storage.load_task(task["id"])
        assert_task_state(updated_task, "auth-required")

    @pytest.mark.asyncio
    async def test_auth_required_metadata_extraction(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test that auth metadata is extracted and stored."""
        agent = MockAgent(response="Auth needed", response_type="auth-required")
        manifest = MockManifest(agent_fn=agent)

        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)

        params = cast(
            TaskSendParams,
            {
                "task_id": task["id"],
                "context_id": task["context_id"],
                "message": message,
            },
        )

        await worker.run_task(params)

        updated_task = await storage.load_task(task["id"])

        # Metadata should contain auth_type and service
        if "metadata" in updated_task:
            # Mock returns these values
            assert updated_task["metadata"].get("auth_type") == "api_key"
            assert updated_task["metadata"].get("service") == "test_service"


class TestConversationHistory:
    """Test conversation history building."""

    @pytest.mark.asyncio
    async def test_history_from_task(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test building history from task history."""
        agent = MockAgent(response="Response")
        manifest = MockManifest(agent_fn=agent)

        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        # Create task with history via submit_task
        msg1 = create_test_message(text="First message")
        task = await storage.submit_task(msg1["context_id"], msg1)

        # Add second message to same task
        msg2 = create_test_message(
            text="Second message", context_id=task["context_id"], task_id=task["id"]
        )
        task = await storage.submit_task(task["context_id"], msg2)

        new_message = create_test_message(text="Third message")
        params = cast(
            TaskSendParams,
            {
                "task_id": task["id"],
                "context_id": task["context_id"],
                "message": new_message,
            },
        )

        await worker.run_task(params)

        # Agent should have been called
        assert agent.call_count == 1

    @pytest.mark.asyncio
    async def test_history_with_reference_tasks(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test building history using referenceTaskIds."""
        agent = MockAgent(response="Refined response")
        manifest = MockManifest(agent_fn=agent)

        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        # Create previous task
        prev_msg = create_test_message(text="Previous message")
        prev_task = await storage.submit_task(prev_msg["context_id"], prev_msg)
        # Mark it as completed
        await storage.update_task(prev_task["id"], state="completed")

        # Create new task referencing previous (same context)
        new_message = create_test_message(
            text="Make it shorter",
            context_id=prev_task["context_id"],
            reference_task_ids=[prev_task["id"]],
        )
        new_task = await storage.submit_task(prev_task["context_id"], new_message)

        params = cast(
            TaskSendParams,
            {
                "task_id": new_task["id"],
                "context_id": new_task["context_id"],
                "message": new_message,
            },
        )

        await worker.run_task(params)

        # Task should complete
        completed = await storage.load_task(new_task["id"])
        assert completed["status"]["state"] in [
            "completed",
            "input-required",
            "auth-required",
        ]


class TestErrorHandling:
    """Test error handling in worker."""

    @pytest.mark.asyncio
    async def test_agent_execution_failure(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test handling of agent execution errors."""
        agent = MockAgent(response="Something went wrong", response_type="error")
        manifest = MockManifest(agent_fn=agent)

        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
        )

        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)

        params = cast(
            TaskSendParams,
            {
                "task_id": task["id"],
                "context_id": task["context_id"],
                "message": message,
            },
        )

        # Should raise exception but also mark task as failed
        with pytest.raises(ValueError, match="Something went wrong"):
            await worker.run_task(params)

        failed_task = await storage.load_task(task["id"])
        assert_task_state(failed_task, "failed")

    @pytest.mark.asyncio
    async def test_task_not_found(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
        mock_manifest: MockManifest,
    ):
        """Test handling of non-existent task."""
        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, mock_manifest),
        )

        params = cast(
            TaskSendParams,
            {
                "task_id": uuid4(),  # Non-existent
                "context_id": uuid4(),
            },
        )

        # Should raise ValueError
        with pytest.raises(ValueError, match="not found"):
            await worker.run_task(params)


class TestLifecycleNotifications:
    """Test lifecycle notification callbacks."""

    @pytest.mark.asyncio
    async def test_lifecycle_callback_invoked(
        self,
        storage: InMemoryStorage,
        scheduler: InMemoryScheduler,
    ):
        """Test that lifecycle notifier is called."""
        agent = MockAgent(response="Done")
        manifest = MockManifest(agent_fn=agent)

        notifications = []

        def notifier(task_id, context_id, state, final):
            notifications.append(
                {
                    "task_id": task_id,
                    "context_id": context_id,
                    "state": state,
                    "final": final,
                }
            )

        worker = ManifestWorker(
            scheduler=scheduler,
            storage=storage,
            manifest=cast(AgentManifest, manifest),
            lifecycle_notifier=notifier,
        )

        message = create_test_message(text="Test")
        task = await storage.submit_task(message["context_id"], message)

        params = cast(
            TaskSendParams,
            {
                "task_id": task["id"],
                "context_id": task["context_id"],
                "message": message,
            },
        )

        await worker.run_task(params)

        # Should have received notifications
        assert len(notifications) > 0
