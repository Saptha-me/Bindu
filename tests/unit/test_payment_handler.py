"""Unit tests for Payment Handler."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bindu.server.workers.helpers.payment_handler import PaymentHandler


class TestPaymentHandler:
    """Test suite for PaymentHandler."""

    def test_parse_payment_payload_none(self):
        """Test parsing None payment payload."""
        result = PaymentHandler.parse_payment_payload(None)
        assert result is None

    def test_parse_payment_payload_valid_dict(self):
        """Test parsing valid payment payload dict."""
        data = {
            "scheme": "onchain",
            "network": "base-sepolia",
            "chainId": "84532",
            "to": "0x1234567890123456789012345678901234567890",
            "amount": "10000",
            "token": "USDC",
            "txHash": "0xabc123",
        }
        result = PaymentHandler.parse_payment_payload(data)
        assert result is not None

    def test_parse_payment_payload_invalid_data(self):
        """Test parsing invalid payment payload data."""
        # Mock PaymentPayload to raise exception on invalid data
        with patch("bindu.server.workers.helpers.payment_handler.PaymentPayload") as mock_pp:
            mock_pp.model_validate.side_effect = Exception("Invalid")
            mock_pp.side_effect = Exception("Invalid")
            result = PaymentHandler.parse_payment_payload({"invalid": "data"})
            assert result is None

    def test_parse_payment_requirements_none(self):
        """Test parsing None payment requirements."""
        result = PaymentHandler.parse_payment_requirements(None)
        assert result is None

    def test_parse_payment_requirements_valid_dict(self):
        """Test parsing valid payment requirements dict."""
        data = {
            "scheme": "onchain",
            "network": "base-sepolia",
            "chainId": "84532",
            "to": "0x1234567890123456789012345678901234567890",
            "amount": "10000",
            "token": "USDC",
        }
        result = PaymentHandler.parse_payment_requirements(data)
        assert result is not None

    def test_parse_payment_requirements_invalid_data(self):
        """Test parsing invalid payment requirements data."""
        with patch("bindu.server.workers.helpers.payment_handler.PaymentRequirements") as mock_pr:
            mock_pr.model_validate.side_effect = Exception("Invalid")
            mock_pr.side_effect = Exception("Invalid")
            result = PaymentHandler.parse_payment_requirements({"invalid": "data"})
            assert result is None

    def test_select_requirement_none_required(self):
        """Test selecting requirement when required is None."""
        result = PaymentHandler.select_requirement(None, None)
        assert result is None

    def test_select_requirement_no_accepts(self):
        """Test selecting requirement when accepts array is missing."""
        result = PaymentHandler.select_requirement({}, None)
        assert result is None

    def test_select_requirement_no_payload_returns_first(self):
        """Test selecting requirement without payload returns first."""
        required = {
            "accepts": [
                {
                    "scheme": "onchain",
                    "network": "base-sepolia",
                    "chainId": "84532",
                    "to": "0x1234567890123456789012345678901234567890",
                    "amount": "10000",
                    "token": "USDC",
                }
            ]
        }
        result = PaymentHandler.select_requirement(required, None)
        assert result is not None

    def test_select_requirement_matching_scheme_and_network(self):
        """Test selecting requirement matching scheme and network."""
        payload = MagicMock()
        payload.scheme = "onchain"
        payload.network = "base-sepolia"

        required = {
            "accepts": [
                {
                    "scheme": "lightning",
                    "network": "bitcoin",
                    "to": "address1",
                    "amount": "5000",
                    "token": "BTC",
                },
                {
                    "scheme": "onchain",
                    "network": "base-sepolia",
                    "chainId": "84532",
                    "to": "0x1234567890123456789012345678901234567890",
                    "amount": "10000",
                    "token": "USDC",
                },
            ]
        }
        result = PaymentHandler.select_requirement(required, payload)
        assert result is not None

    def test_select_requirement_no_match_returns_first(self):
        """Test selecting requirement with no match returns first."""
        payload = MagicMock()
        payload.scheme = "nonexistent"
        payload.network = "nonexistent"

        required = {
            "accepts": [
                {
                    "scheme": "onchain",
                    "network": "base-sepolia",
                    "chainId": "84532",
                    "to": "0x1234567890123456789012345678901234567890",
                    "amount": "10000",
                    "token": "USDC",
                }
            ]
        }
        result = PaymentHandler.select_requirement(required, payload)
        assert result is not None

    @pytest.mark.asyncio
    async def test_settle_payment_success(self):
        """Test successful payment settlement."""
        task = {"id": "task-123", "context_id": "ctx-456"}
        results = {"output": "test result"}
        state = "completed"
        payload = MagicMock()
        requirements = MagicMock()
        storage = MagicMock()
        terminal_state_handler = AsyncMock()

        # Mock FacilitatorClient
        with patch(
            "bindu.server.workers.helpers.payment_handler.FacilitatorClient"
        ) as mock_facilitator_class:
            mock_facilitator = MagicMock()
            mock_facilitator_class.return_value = mock_facilitator

            # Mock successful settlement
            settle_response = MagicMock()
            settle_response.success = True
            settle_response.model_dump = MagicMock(
                return_value={"receipt": "test-receipt"}
            )
            mock_facilitator.settle = AsyncMock(return_value=settle_response)

            await PaymentHandler.settle_payment(
                task,
                results,
                state,
                payload,
                requirements,
                storage,
                terminal_state_handler,
            )

            # Verify settlement was called
            mock_facilitator.settle.assert_called_once_with(payload, requirements)

            # Verify terminal state handler was called
            terminal_state_handler.assert_called_once()
            call_args = terminal_state_handler.call_args[0]
            assert call_args[0] == task
            assert call_args[1] == results
            assert call_args[2] == state

    @pytest.mark.asyncio
    async def test_settle_payment_failure(self):
        """Test payment settlement failure."""
        task = {"id": "task-123", "context_id": "ctx-456"}
        results = {"output": "test result"}
        state = "completed"
        payload = MagicMock()
        requirements = MagicMock()
        storage = MagicMock()
        storage.update_task = AsyncMock()
        terminal_state_handler = AsyncMock()

        # Mock FacilitatorClient
        with patch(
            "bindu.server.workers.helpers.payment_handler.FacilitatorClient"
        ) as mock_facilitator_class:
            mock_facilitator = MagicMock()
            mock_facilitator_class.return_value = mock_facilitator

            # Mock failed settlement
            settle_response = MagicMock()
            settle_response.success = False
            settle_response.error_reason = "Insufficient funds"
            settle_response.model_dump = MagicMock(
                return_value={"error": "Insufficient funds"}
            )
            mock_facilitator.settle = AsyncMock(return_value=settle_response)

            await PaymentHandler.settle_payment(
                task,
                results,
                state,
                payload,
                requirements,
                storage,
                terminal_state_handler,
            )

            # Verify settlement was called
            mock_facilitator.settle.assert_called_once_with(payload, requirements)

            # Verify task was updated to input-required
            storage.update_task.assert_called_once()
            call_args = storage.update_task.call_args
            assert call_args[0][0] == "task-123"
            assert call_args[1]["state"] == "input-required"

            # Terminal state handler should NOT be called
            terminal_state_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_settle_payment_exception(self):
        """Test payment settlement with exception."""
        task = {"id": "task-123", "context_id": "ctx-456"}
        results = {"output": "test result"}
        state = "completed"
        payload = MagicMock()
        requirements = MagicMock()
        storage = MagicMock()
        storage.update_task = AsyncMock()
        terminal_state_handler = AsyncMock()

        # Mock FacilitatorClient to raise exception
        with patch(
            "bindu.server.workers.helpers.payment_handler.FacilitatorClient"
        ) as mock_facilitator_class:
            mock_facilitator = MagicMock()
            mock_facilitator_class.return_value = mock_facilitator
            mock_facilitator.settle = AsyncMock(
                side_effect=Exception("Network error")
            )

            await PaymentHandler.settle_payment(
                task,
                results,
                state,
                payload,
                requirements,
                storage,
                terminal_state_handler,
            )

            # Verify task was updated to input-required
            storage.update_task.assert_called_once()
            call_args = storage.update_task.call_args
            assert call_args[0][0] == "task-123"
            assert call_args[1]["state"] == "input-required"

            # Terminal state handler should NOT be called
            terminal_state_handler.assert_not_called()

    @pytest.mark.asyncio
    async def test_settle_payment_with_lifecycle_notifier(self):
        """Test payment settlement with lifecycle notifier."""
        task = {"id": "task-123", "context_id": "ctx-456"}
        results = {"output": "test result"}
        state = "completed"
        payload = MagicMock()
        requirements = MagicMock()
        storage = MagicMock()
        storage.update_task = AsyncMock()
        terminal_state_handler = AsyncMock()
        lifecycle_notifier = MagicMock(return_value=None)

        # Mock FacilitatorClient
        with patch(
            "bindu.server.workers.helpers.payment_handler.FacilitatorClient"
        ) as mock_facilitator_class:
            mock_facilitator = MagicMock()
            mock_facilitator_class.return_value = mock_facilitator

            # Mock failed settlement
            settle_response = MagicMock()
            settle_response.success = False
            settle_response.error_reason = "Test error"
            settle_response.model_dump = MagicMock(return_value={"error": "Test error"})
            mock_facilitator.settle = AsyncMock(return_value=settle_response)

            await PaymentHandler.settle_payment(
                task,
                results,
                state,
                payload,
                requirements,
                storage,
                terminal_state_handler,
                lifecycle_notifier,
            )

            # Verify lifecycle notifier was called
            lifecycle_notifier.assert_called_once_with(
                "task-123", "ctx-456", "input-required", False
            )

    @pytest.mark.asyncio
    async def test_settle_payment_with_async_lifecycle_notifier(self):
        """Test payment settlement with async lifecycle notifier."""
        task = {"id": "task-123", "context_id": "ctx-456"}
        results = {"output": "test result"}
        state = "completed"
        payload = MagicMock()
        requirements = MagicMock()
        storage = MagicMock()
        storage.update_task = AsyncMock()
        terminal_state_handler = AsyncMock()
        lifecycle_notifier = AsyncMock()

        # Mock FacilitatorClient
        with patch(
            "bindu.server.workers.helpers.payment_handler.FacilitatorClient"
        ) as mock_facilitator_class:
            mock_facilitator = MagicMock()
            mock_facilitator_class.return_value = mock_facilitator

            # Mock failed settlement
            settle_response = MagicMock()
            settle_response.success = False
            settle_response.error_reason = "Test error"
            settle_response.model_dump = MagicMock(return_value={"error": "Test error"})
            mock_facilitator.settle = AsyncMock(return_value=settle_response)

            await PaymentHandler.settle_payment(
                task,
                results,
                state,
                payload,
                requirements,
                storage,
                terminal_state_handler,
                lifecycle_notifier,
            )

            # Verify async lifecycle notifier was awaited
            lifecycle_notifier.assert_called_once_with(
                "task-123", "ctx-456", "input-required", False
            )

    @pytest.mark.asyncio
    async def test_settle_payment_lifecycle_notifier_exception(self):
        """Test payment settlement handles lifecycle notifier exception."""
        task = {"id": "task-123", "context_id": "ctx-456"}
        results = {"output": "test result"}
        state = "completed"
        payload = MagicMock()
        requirements = MagicMock()
        storage = MagicMock()
        storage.update_task = AsyncMock()
        terminal_state_handler = AsyncMock()
        lifecycle_notifier = MagicMock(side_effect=Exception("Notifier error"))

        # Mock FacilitatorClient
        with patch(
            "bindu.server.workers.helpers.payment_handler.FacilitatorClient"
        ) as mock_facilitator_class:
            mock_facilitator = MagicMock()
            mock_facilitator_class.return_value = mock_facilitator

            # Mock failed settlement
            settle_response = MagicMock()
            settle_response.success = False
            settle_response.error_reason = "Test error"
            settle_response.model_dump = MagicMock(return_value={"error": "Test error"})
            mock_facilitator.settle = AsyncMock(return_value=settle_response)

            # Should not raise exception
            await PaymentHandler.settle_payment(
                task,
                results,
                state,
                payload,
                requirements,
                storage,
                terminal_state_handler,
                lifecycle_notifier,
            )

            # Task should still be updated
            storage.update_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_settlement_failure(self):
        """Test _handle_settlement_failure method."""
        task = {"id": "task-123", "context_id": "ctx-456"}
        error_reason = "Payment failed"
        receipt = {"error": "test error"}
        storage = MagicMock()
        storage.update_task = AsyncMock()

        await PaymentHandler._handle_settlement_failure(
            task, error_reason, receipt, storage
        )

        # Verify task was updated
        storage.update_task.assert_called_once()
        call_args = storage.update_task.call_args
        assert call_args[0][0] == "task-123"
        assert call_args[1]["state"] == "input-required"
        assert "new_messages" in call_args[1]
        assert "metadata" in call_args[1]

    @pytest.mark.asyncio
    async def test_handle_settlement_failure_with_notifier(self):
        """Test _handle_settlement_failure with lifecycle notifier."""
        task = {"id": "task-123", "context_id": "ctx-456"}
        error_reason = "Payment failed"
        receipt = None
        storage = MagicMock()
        storage.update_task = AsyncMock()
        lifecycle_notifier = MagicMock(return_value=None)

        await PaymentHandler._handle_settlement_failure(
            task, error_reason, receipt, storage, lifecycle_notifier
        )

        # Verify notifier was called
        lifecycle_notifier.assert_called_once_with(
            "task-123", "ctx-456", "input-required", False
        )
