"""Minimal tests for ManifestWorker."""

from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4
import pytest

from bindu.common.protocol.types import Task, TaskSendParams
from bindu.server.workers.manifest_worker import ManifestWorker


class TestManifestWorker:
    """Test ManifestWorker functionality."""

    def test_build_message_history_delegates_to_converter(self):
        """Test building message history delegates to MessageConverter."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        # The method delegates to MessageConverter.to_chat_format
        result = worker.build_message_history(messages)  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]

        # Result type depends on MessageConverter implementation
        assert isinstance(result, list)

    def test_build_artifacts(self):
        """Test building artifacts from result."""
        mock_manifest = Mock()
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        result = "Task completed successfully"

        artifacts = worker.build_artifacts(result)

        assert len(artifacts) > 0
        assert "parts" in artifacts[0]

    @pytest.mark.asyncio
    async def test_handle_task_failure(self):
        """Test handling task failure."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        task = cast(
            Task,
            {
                "id": uuid4(),
                "context_id": uuid4(),
                "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
            },
        )

        await worker._handle_task_failure(task, "Test error")

        mock_storage.update_task.assert_called_once()
        call_args = mock_storage.update_task.call_args
        assert call_args[0][0] == task["id"]
        assert call_args[1]["state"] == "failed"

    @pytest.mark.asyncio
    async def test_notify_lifecycle_with_callback(self):
        """Test lifecycle notification with callback."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()
        mock_callback = Mock()

        worker = ManifestWorker(
            manifest=mock_manifest,
            scheduler=mock_scheduler,
            storage=mock_storage,
            lifecycle_notifier=mock_callback,
        )

        task_id = uuid4()
        context_id = uuid4()

        await worker._notify_lifecycle(task_id, context_id, "completed", True)

        # Notifier is called with the 5-arg shape (task_id, context_id, state,
        # final, status_message) introduced in 270f4b94. status_message defaults
        # to None when _notify_lifecycle is called without one.
        mock_callback.assert_called_once_with(
            task_id, context_id, "completed", True, None
        )

    @pytest.mark.asyncio
    async def test_notify_lifecycle_without_callback(self):
        """Test lifecycle notification without callback."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        task_id = uuid4()
        context_id = uuid4()

        # Should not raise error
        await worker._notify_lifecycle(task_id, context_id, "completed", True)

    @pytest.mark.asyncio
    async def test_settle_payment_handles_missing_context(self):
        """Test payment settlement with missing context returns error."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        # Empty payment context should return error
        payment_context = {}

        result = await worker._settle_payment(payment_context)

        # Should return error status
        assert "x402_status" in result or "error" in str(result).lower()

    def test_add_state_change_event(self):
        """Test adding state change event."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        # Should not raise error
        worker._add_state_change_event("working", "pending")

    def test_log_notification_error(self):
        """Test logging notification error."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        task_id = uuid4()
        context_id = uuid4()
        error = Exception("Test error")

        # Should not raise error
        worker._log_notification_error("Artifact", task_id, context_id, error)

    @pytest.mark.asyncio
    async def test_cancel_task(self):
        """Test canceling a task."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
        }
        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        await worker.cancel_task({"task_id": task_id})

        mock_storage.update_task.assert_called_once_with(task_id, state="canceled")

    @pytest.mark.asyncio
    async def test_cancel_task_not_found(self):
        """Test canceling a task that doesn't exist."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()
        mock_storage.load_task.return_value = None

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        task_id = uuid4()
        await worker.cancel_task({"task_id": task_id})

        mock_storage.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_build_complete_message_history_with_references(self):
        """Test building message history with reference task IDs."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        ref_task_id = uuid4()

        task = cast(
            Task,
            {
                "id": task_id,
                "context_id": context_id,
                "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
                "history": [
                    {
                        "role": "user",
                        "content": "test",
                        "reference_task_ids": [ref_task_id],
                    }
                ],
            },
        )

        ref_task = {
            "id": ref_task_id,
            "context_id": context_id,
            "history": [{"role": "user", "content": "previous"}],
        }

        mock_storage.load_task.return_value = ref_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        history = await worker._build_complete_message_history(task)

        assert isinstance(history, list)
        mock_storage.load_task.assert_called()

    @pytest.mark.asyncio
    async def test_build_complete_message_history_without_references(self):
        """Test building message history without reference task IDs."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        task = cast(
            Task,
            {
                "id": task_id,
                "context_id": context_id,
                "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
                "history": [{"role": "user", "content": "test"}],
            },
        )

        mock_storage.load_context_tasks.return_value = [task]

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        history = await worker._build_complete_message_history(task)

        assert isinstance(history, list)

    @pytest.mark.asyncio
    async def test_settle_payment_with_valid_context(self):
        """Test payment settlement with valid payment context."""
        mock_manifest = Mock()
        mock_manifest.x402_extension = Mock()
        mock_manifest.x402_extension.facilitator_config = Mock()

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        payment_context = {"session_id": "sess123", "amount": "100", "token": "USDC"}

        result = await worker._settle_payment(payment_context)

        assert result is not None

    @pytest.mark.asyncio
    async def test_handle_intermediate_state(self):
        """Test handling intermediate task state."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        task = cast(
            Task,
            {
                "id": task_id,
                "context_id": context_id,
                "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
            },
        )

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        await worker._handle_intermediate_state(
            task, "input-required", "Please provide input"
        )

        mock_storage.update_task.assert_called()

    @pytest.mark.asyncio
    async def test_handle_terminal_state(self):
        """Test handling terminal task state."""
        mock_manifest = Mock()
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        task = cast(
            Task,
            {
                "id": task_id,
                "context_id": context_id,
                "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
            },
        )

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        await worker._handle_terminal_state(task, "Task completed", "completed")

        mock_storage.update_task.assert_called()

    @pytest.mark.asyncio
    async def test_handle_terminal_state_with_settlement_metadata(self):
        """Terminal state attaches pre-settled metadata to the task."""
        mock_manifest = Mock()
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.x402_extension = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        task = cast(
            Task,
            {
                "id": task_id,
                "context_id": context_id,
                "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
            },
        )

        settlement_metadata = {
            "x402.payment.status": "payment-completed",
            "x402.payment.receipts": [{"tx_hash": "0xreceipt"}],
        }

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        await worker._handle_terminal_state(
            task, "Task completed", "completed", settlement_metadata=settlement_metadata
        )

        mock_storage.update_task.assert_called()
        # The settlement metadata is now attached to the task.
        update_kwargs = mock_storage.update_task.call_args.kwargs
        assert update_kwargs.get("metadata") == settlement_metadata

    def test_add_state_change_event_with_error(self):
        """Test adding state change event with error."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        worker._add_state_change_event("failed", "working", error="Test error")

    def test_add_state_change_event_without_from_state(self):
        """Test adding state change event without from_state."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        worker._add_state_change_event("completed")

    @pytest.mark.asyncio
    async def test_run_task_basic_flow(self):
        """Test basic task execution flow."""
        mock_manifest = Mock()
        mock_manifest.run = Mock(return_value="Task completed")
        mock_manifest.name = "test-agent"
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.enable_system_message = False
        mock_manifest.enable_context_based_history = False

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "test"}],
        }

        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(TaskSendParams, {"task_id": task_id, "context_id": context_id})

        await worker.run_task(params)

        mock_storage.update_task.assert_called()
        mock_manifest.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_task_with_input_required_response(self):
        """Test task execution with input-required response."""
        mock_manifest = Mock()
        mock_manifest.run = Mock(
            return_value='{"state": "input-required", "prompt": "Need more info"}'
        )
        mock_manifest.name = "test-agent"
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.enable_system_message = False
        mock_manifest.enable_context_based_history = False

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "test"}],
        }

        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(TaskSendParams, {"task_id": task_id, "context_id": context_id})

        await worker.run_task(params)

        mock_storage.update_task.assert_called()

    @pytest.mark.asyncio
    async def test_run_task_with_auth_required_response(self):
        """Test task execution with auth-required response."""
        mock_manifest = Mock()
        mock_manifest.run = Mock(
            return_value='{"state": "auth-required", "prompt": "Login needed"}'
        )
        mock_manifest.name = "test-agent"
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.enable_system_message = False
        mock_manifest.enable_context_based_history = False

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "test"}],
        }

        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(TaskSendParams, {"task_id": task_id, "context_id": context_id})

        await worker.run_task(params)

        mock_storage.update_task.assert_called()

    @pytest.mark.asyncio
    async def test_run_task_with_payment_context(self):
        """Test task execution with payment context."""
        mock_manifest = Mock()
        mock_manifest.run = Mock(return_value="Task completed")
        mock_manifest.name = "test-agent"
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.enable_system_message = False
        mock_manifest.enable_context_based_history = False
        mock_manifest.x402_extension = Mock()

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "test"}],
        }

        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(
            TaskSendParams,
            {
                "task_id": task_id,
                "context_id": context_id,
                "payment_context": {"session_id": "sess123"},
            },
        )

        await worker.run_task(params)

        mock_storage.update_task.assert_called()

    @pytest.mark.asyncio
    async def test_run_task_not_found(self):
        """Test task execution when task doesn't exist."""
        mock_manifest = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()
        mock_storage.load_task.return_value = None

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(TaskSendParams, {"task_id": uuid4(), "context_id": uuid4()})

        with pytest.raises(ValueError, match="not found"):
            await worker.run_task(params)

    @pytest.mark.asyncio
    async def test_run_task_with_agent_error(self):
        """Test task execution when agent raises error."""
        mock_manifest = Mock()
        mock_manifest.run = Mock(side_effect=Exception("Agent error"))
        mock_manifest.name = "test-agent"
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.enable_system_message = False
        mock_manifest.enable_context_based_history = False

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "test"}],
        }

        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(TaskSendParams, {"task_id": task_id, "context_id": context_id})

        with pytest.raises(Exception, match="Agent error"):
            await worker.run_task(params)

        # Should have updated task to failed state
        assert any(
            call[1].get("state") == "failed"
            for call in mock_storage.update_task.call_args_list
        )

    @pytest.mark.asyncio
    async def test_run_task_with_system_message(self):
        """Test task execution with system message enabled."""
        from unittest.mock import patch

        mock_manifest = Mock()
        mock_manifest.run = Mock(return_value="Task completed")
        mock_manifest.name = "test-agent"
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.enable_system_message = True
        mock_manifest.enable_context_based_history = False

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "test"}],
        }

        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(TaskSendParams, {"task_id": task_id, "context_id": context_id})

        with patch(
            "bindu.server.workers.manifest_worker.app_settings"
        ) as mock_settings:
            mock_settings.agent.enable_structured_responses = True
            mock_settings.agent.structured_response_system_prompt = "System prompt"
            mock_settings.agent.terminal_states = frozenset(
                ["completed", "failed", "canceled"]
            )

            await worker.run_task(params)

        mock_manifest.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_task_with_context_based_history(self):
        """Test task execution with context-based history."""
        mock_manifest = Mock()
        mock_manifest.run = Mock(return_value="Task completed")
        mock_manifest.name = "test-agent"
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.enable_system_message = False
        mock_manifest.enable_context_based_history = True

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        prev_task_id = uuid4()

        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "current"}],
        }

        prev_task = {
            "id": prev_task_id,
            "context_id": context_id,
            "history": [{"role": "user", "content": "previous"}],
        }

        mock_storage.load_task.return_value = mock_task
        mock_storage.list_tasks_by_context.return_value = [prev_task, mock_task]

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        params = cast(TaskSendParams, {"task_id": task_id, "context_id": context_id})

        await worker.run_task(params)

        mock_storage.list_tasks_by_context.assert_called_once_with(context_id)

    @pytest.mark.asyncio
    async def test_settle_payment_with_facilitator(self):
        """Test payment settlement with facilitator client."""
        from unittest.mock import patch

        mock_manifest = Mock()
        mock_manifest.x402_extension = Mock()
        mock_manifest.x402_extension.facilitator_config = Mock()

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        payment_context = {"session_id": "sess123", "amount": "100", "token": "USDC"}

        with patch(
            "bindu.server.workers.manifest_worker.HTTPFacilitatorClient"
        ) as mock_client_class:
            mock_client = AsyncMock()
            mock_client.settle_payment = AsyncMock(return_value={"status": "success"})
            mock_client_class.return_value = mock_client

            result = await worker._settle_payment(payment_context)

            assert result is not None

    @pytest.mark.asyncio
    async def test_settle_exception_persists_recovery_metadata(self):
        """When settle raises, the task metadata must carry enough to reconcile.

        Issue #562 calls out that today we lose the EIP-3009 nonce and signed
        authorization on a settle exception (just str(e) is stored). A
        recovery worker or operator can't tell whether the on-chain transfer
        actually went through. The fix persists nonce + authorization.
        """
        from unittest.mock import patch

        import asyncio

        mock_manifest = Mock()
        mock_manifest.x402_extension = Mock()
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        payment_context = {
            "payment_payload": {
                "payload": {
                    "authorization": {
                        "nonce": "0xdeadbeef",
                        "from": "0xCarol",
                        "to": "0xAlice",
                        "value": "1000000",
                        "validBefore": "1735000300",
                    }
                },
                "network": "base-sepolia",
            },
            "payment_requirements": {},
        }

        # Patch on the x402 module — `_settle_payment` does a local
        # `from x402 import PaymentPayload, PaymentRequirements`, which
        # resolves the attribute on x402 at call time.
        with (
            patch("x402.PaymentPayload") as mock_pp,
            patch("x402.PaymentRequirements") as mock_pr,
            patch(
                "bindu.server.workers.manifest_worker.HTTPFacilitatorClient"
            ) as mock_fac_class,
        ):
            mock_pp.model_validate = Mock(return_value=Mock())
            mock_pr.model_validate = Mock(return_value=Mock())
            mock_fac = AsyncMock()
            mock_fac.settle = AsyncMock(side_effect=asyncio.TimeoutError("upstream"))
            mock_fac_class.return_value = mock_fac

            result = await worker._settle_payment(payment_context)

        assert result["x402.payment.status"] == "payment-failed"
        # Reconciliation needs the nonce and the full authorization block —
        # str(e) alone is not enough.
        assert result.get("x402_nonce") == "0xdeadbeef"
        assert result.get("x402_authorization", {}).get("from") == "0xCarol"
        assert result.get("x402_network") == "base-sepolia"

    @pytest.mark.asyncio
    async def test_settle_first_failure_does_not_invoke_manifest(self):
        """Settle-first: a failed settlement must skip manifest.run entirely.

        With settle-first ordering, a payer who drained their wallet between
        verify and settle (Scenario 1) — or whose nonce lost a parallel-settle
        race (Scenario 3) — never triggers an LLM call. The agent's OpenAI
        bill is $0 instead of $0.30.
        """
        mock_manifest = Mock()
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.name = "test-agent"
        mock_manifest.enable_system_message = False
        mock_manifest.enable_context_based_history = False
        mock_manifest.x402_extension = Mock()
        mock_manifest.run = Mock(return_value="should not be called")

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "test"}],
        }
        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        # Facilitator reports settlement failure (e.g. payer drained wallet).
        worker._settle_payment = AsyncMock(  # type: ignore[method-assign] # ty: ignore[invalid-assignment]
            return_value={
                "x402.payment.status": "payment-failed",
                "x402.payment.error": "transfer reverted: insufficient balance",
            }
        )

        params = cast(
            TaskSendParams,
            {
                "task_id": task_id,
                "context_id": context_id,
                "payment_context": {
                    "payment_payload": {
                        "payload": {"authorization": {"nonce": "0xdeadbeef"}}
                    },
                    "payment_requirements": {},
                },
            },
        )

        await worker.run_task(params)

        # The whole point: no LLM call burned.
        mock_manifest.run.assert_not_called()

        # Task ends in failed, not completed.
        update_calls = mock_storage.update_task.call_args_list
        states = [call.kwargs.get("state") for call in update_calls]
        assert "completed" not in states
        assert "failed" in states

    @pytest.mark.asyncio
    async def test_settle_first_runs_manifest_only_after_settle(self):
        """Settle-first: settle() must complete before manifest.run() starts.

        Asserts call ordering. Today (verify→execute→settle) manifest runs
        first; under settle-first, settle runs first.
        """
        call_order: list[str] = []

        mock_manifest = Mock()
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.name = "test-agent"
        mock_manifest.enable_system_message = False
        mock_manifest.enable_context_based_history = False
        mock_manifest.x402_extension = Mock()

        def manifest_run(_messages):
            call_order.append("manifest")
            return "result"

        mock_manifest.run = manifest_run

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "test"}],
        }
        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        async def fake_settle(_ctx):
            call_order.append("settle")
            return {
                "x402.payment.status": "payment-completed",
                "x402.payment.receipts": [{"tx_hash": "0xreceipt"}],
            }

        worker._settle_payment = fake_settle  # type: ignore[method-assign] # ty: ignore[invalid-assignment]

        params = cast(
            TaskSendParams,
            {
                "task_id": task_id,
                "context_id": context_id,
                "payment_context": {
                    "payment_payload": {
                        "payload": {"authorization": {"nonce": "0xfeed"}}
                    },
                    "payment_requirements": {},
                },
            },
        )

        await worker.run_task(params)

        assert call_order == ["settle", "manifest"], (
            f"expected settle before manifest, got: {call_order}"
        )

    @pytest.mark.asyncio
    async def test_work_failure_after_settle_persists_orphan_payment(self):
        """Settle succeeded, work raised — task carries 'orphan payment' metadata.

        Under settle-first, a manifest.run exception happens AFTER funds
        moved on-chain. The user paid and got nothing. We can't refund
        automatically (x402 has no refund primitive), so we persist enough
        metadata for an operator to handle reconciliation manually.
        """
        mock_manifest = Mock()
        mock_manifest.did_extension = Mock()
        mock_manifest.did_extension.did = "did:example:123"
        mock_manifest.name = "test-agent"
        mock_manifest.enable_system_message = False
        mock_manifest.enable_context_based_history = False
        mock_manifest.x402_extension = Mock()
        mock_manifest.run = Mock(side_effect=RuntimeError("upstream provider 500"))

        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()
        mock_task = {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": "submitted", "timestamp": "2024-01-01T00:00:00Z"},
            "history": [{"role": "user", "content": "test"}],
        }
        mock_storage.load_task.return_value = mock_task

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        worker._settle_payment = AsyncMock(  # type: ignore[method-assign] # ty: ignore[invalid-assignment]
            return_value={
                "x402.payment.status": "payment-completed",
                "x402.payment.receipts": [{"tx_hash": "0xpaid"}],
                "x402_nonce": "0xfeed",
            }
        )

        params = cast(
            TaskSendParams,
            {
                "task_id": task_id,
                "context_id": context_id,
                "payment_context": {
                    "payment_payload": {
                        "payload": {"authorization": {"nonce": "0xfeed"}}
                    },
                    "payment_requirements": {},
                },
            },
        )

        with pytest.raises(RuntimeError, match="upstream provider 500"):
            await worker.run_task(params)

        # Task is failed, but the metadata records the orphan payment so
        # an operator can issue a manual refund.
        failed_calls = [
            call
            for call in mock_storage.update_task.call_args_list
            if call.kwargs.get("state") == "failed"
        ]
        assert failed_calls, "task should be marked failed after work raises"
        # The most recent failed-state update is the one that should carry the
        # orphan payment metadata.
        last_failed_meta = failed_calls[-1].kwargs.get("metadata") or {}
        assert last_failed_meta.get("x402.payment.status") == "payment-orphaned", (
            "orphan payment must be flagged distinctly from a failed settlement; "
            f"got metadata={last_failed_meta}"
        )
        assert last_failed_meta.get("x402_nonce") == "0xfeed"

    @pytest.mark.asyncio
    async def test_build_complete_message_history_with_context_disabled(self):
        """Test building message history with context-based history disabled."""
        mock_manifest = Mock()
        mock_manifest.enable_context_based_history = False
        mock_scheduler = Mock()
        mock_storage = AsyncMock()

        task_id = uuid4()
        context_id = uuid4()

        task = cast(
            Task,
            {
                "id": task_id,
                "context_id": context_id,
                "status": {"state": "working", "timestamp": "2024-01-01T00:00:00Z"},
                "history": [{"role": "user", "content": "test"}],
            },
        )

        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )

        history = await worker._build_complete_message_history(task)

        assert isinstance(history, list)
        # Should not call list_tasks_by_context when disabled
        mock_storage.list_tasks_by_context.assert_not_called()


class TestWorkerPauseResume:
    """Tests for _handle_pause and _handle_resume on the base Worker (via ManifestWorker)."""

    def _make_worker(self):
        mock_manifest = Mock()
        mock_scheduler = AsyncMock()
        mock_storage = AsyncMock()
        worker = ManifestWorker(
            manifest=mock_manifest, scheduler=mock_scheduler, storage=mock_storage
        )
        return worker, mock_storage, mock_scheduler

    def _make_task(self, task_id, context_id, state):
        return {
            "id": task_id,
            "context_id": context_id,
            "status": {"state": state, "timestamp": "2024-01-01T00:00:00Z"},
        }

    @pytest.mark.asyncio
    @pytest.mark.parametrize("state", ["working", "submitted", "input-required", "auth-required"])
    async def test_pause_active_task_transitions_to_suspended(self, state):
        worker, mock_storage, _ = self._make_worker()
        task_id = uuid4()
        mock_storage.load_task.return_value = self._make_task(task_id, uuid4(), state)

        await worker._handle_pause({"task_id": task_id})

        mock_storage.update_task.assert_called_once_with(task_id, state="suspended")

    @pytest.mark.asyncio
    async def test_pause_terminal_task_is_noop(self):
        worker, mock_storage, _ = self._make_worker()
        task_id = uuid4()
        mock_storage.load_task.return_value = self._make_task(task_id, uuid4(), "completed")

        await worker._handle_pause({"task_id": task_id})

        mock_storage.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_pause_unknown_task_is_noop(self):
        worker, mock_storage, _ = self._make_worker()
        mock_storage.load_task.return_value = None

        await worker._handle_pause({"task_id": uuid4()})

        mock_storage.update_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_suspended_task_resubmits(self):
        worker, mock_storage, mock_scheduler = self._make_worker()
        task_id = uuid4()
        context_id = uuid4()
        mock_storage.load_task.return_value = self._make_task(task_id, context_id, "suspended")

        await worker._handle_resume({"task_id": task_id})

        mock_storage.update_task.assert_called_once_with(task_id, state="submitted")
        mock_scheduler.run_task.assert_called_once()
        run_params = mock_scheduler.run_task.call_args[0][0]
        assert run_params["task_id"] == task_id
        assert run_params["context_id"] == context_id

    @pytest.mark.asyncio
    async def test_resume_non_suspended_task_is_noop(self):
        worker, mock_storage, mock_scheduler = self._make_worker()
        task_id = uuid4()
        mock_storage.load_task.return_value = self._make_task(task_id, uuid4(), "working")

        await worker._handle_resume({"task_id": task_id})

        mock_storage.update_task.assert_not_called()
        mock_scheduler.run_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_unknown_task_is_noop(self):
        worker, mock_storage, mock_scheduler = self._make_worker()
        mock_storage.load_task.return_value = None

        await worker._handle_resume({"task_id": uuid4()})

        mock_storage.update_task.assert_not_called()
        mock_scheduler.run_task.assert_not_called()

    @pytest.mark.asyncio
    async def test_resume_rolls_back_to_suspended_on_enqueue_failure(self):
        worker, mock_storage, mock_scheduler = self._make_worker()
        task_id = uuid4()
        context_id = uuid4()
        mock_storage.load_task.return_value = self._make_task(task_id, context_id, "suspended")
        mock_scheduler.run_task.side_effect = RuntimeError("queue full")

        with pytest.raises(RuntimeError, match="queue full"):
            await worker._handle_resume({"task_id": task_id})

        # First call sets submitted, second call rolls back to suspended
        calls = mock_storage.update_task.call_args_list
        assert calls[0] == ((task_id,), {"state": "submitted"})
        assert calls[1] == ((task_id,), {"state": "suspended"})
