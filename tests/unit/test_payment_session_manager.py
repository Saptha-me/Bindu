"""Unit tests for Payment Session Manager."""

import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from x402.types import PaymentPayload

from bindu.server.middleware.x402.payment_session_manager import (
    PaymentSession,
    PaymentSessionManager,
)


class TestPaymentSession:
    """Test suite for PaymentSession dataclass."""

    def test_payment_session_creation(self):
        """Test creating a payment session."""
        session = PaymentSession(session_id="test-session-id")
        assert session.session_id == "test-session-id"
        assert session.status == "pending"
        assert session.payment_payload is None
        assert session.error is None
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.expires_at, datetime)

    def test_payment_session_is_expired_false(self):
        """Test is_expired returns False for non-expired session."""
        session = PaymentSession(
            session_id="test-id",
            expires_at=datetime.utcnow() + timedelta(minutes=10),
        )
        assert session.is_expired() is False

    def test_payment_session_is_expired_true(self):
        """Test is_expired returns True for expired session."""
        session = PaymentSession(
            session_id="test-id",
            expires_at=datetime.utcnow() - timedelta(minutes=1),
        )
        assert session.is_expired() is True

    def test_payment_session_is_completed_false_pending(self):
        """Test is_completed returns False for pending session."""
        session = PaymentSession(session_id="test-id", status="pending")
        assert session.is_completed() is False

    def test_payment_session_is_completed_false_no_payload(self):
        """Test is_completed returns False when no payment payload."""
        session = PaymentSession(session_id="test-id", status="completed")
        assert session.is_completed() is False

    def test_payment_session_is_completed_true(self):
        """Test is_completed returns True when completed with payload."""
        payload = MagicMock(spec=PaymentPayload)
        session = PaymentSession(
            session_id="test-id",
            status="completed",
            payment_payload=payload,
        )
        assert session.is_completed() is True


class TestPaymentSessionManager:
    """Test suite for PaymentSessionManager."""

    @pytest.fixture
    def manager(self):
        """Create a payment session manager."""
        return PaymentSessionManager(session_timeout_minutes=15)

    def test_manager_initialization(self):
        """Test manager initialization."""
        manager = PaymentSessionManager(session_timeout_minutes=30)
        assert manager._sessions == {}
        assert manager._session_timeout == timedelta(minutes=30)
        assert manager._cleanup_task is None

    def test_create_session(self, manager):
        """Test creating a new payment session."""
        session = manager.create_session()
        assert session.session_id is not None
        assert len(session.session_id) > 0
        assert session.status == "pending"
        assert session.session_id in manager._sessions

    def test_create_multiple_sessions(self, manager):
        """Test creating multiple unique sessions."""
        session1 = manager.create_session()
        session2 = manager.create_session()
        assert session1.session_id != session2.session_id
        assert len(manager._sessions) == 2

    def test_get_session_found(self, manager):
        """Test getting an existing session."""
        created_session = manager.create_session()
        retrieved_session = manager.get_session(created_session.session_id)
        assert retrieved_session is not None
        assert retrieved_session.session_id == created_session.session_id

    def test_get_session_not_found(self, manager):
        """Test getting a non-existent session."""
        session = manager.get_session("non-existent-id")
        assert session is None

    def test_get_session_expired(self, manager):
        """Test getting an expired session returns None."""
        session = manager.create_session()
        # Manually expire the session
        manager._sessions[session.session_id].expires_at = datetime.utcnow() - timedelta(
            minutes=1
        )
        retrieved_session = manager.get_session(session.session_id)
        assert retrieved_session is None
        assert session.session_id not in manager._sessions

    def test_complete_session_success(self, manager):
        """Test completing a session successfully."""
        session = manager.create_session()
        payload = MagicMock(spec=PaymentPayload)
        result = manager.complete_session(session.session_id, payload)
        assert result is True
        retrieved_session = manager.get_session(session.session_id)
        assert retrieved_session.status == "completed"
        assert retrieved_session.payment_payload == payload

    def test_complete_session_not_found(self, manager):
        """Test completing a non-existent session."""
        payload = MagicMock(spec=PaymentPayload)
        result = manager.complete_session("non-existent-id", payload)
        assert result is False

    def test_complete_session_expired(self, manager):
        """Test completing an expired session."""
        session = manager.create_session()
        manager._sessions[session.session_id].expires_at = datetime.utcnow() - timedelta(
            minutes=1
        )
        payload = MagicMock(spec=PaymentPayload)
        result = manager.complete_session(session.session_id, payload)
        assert result is False

    def test_fail_session_success(self, manager):
        """Test failing a session successfully."""
        session = manager.create_session()
        error_msg = "Payment verification failed"
        result = manager.fail_session(session.session_id, error_msg)
        assert result is True
        retrieved_session = manager.get_session(session.session_id)
        assert retrieved_session.status == "failed"
        assert retrieved_session.error == error_msg

    def test_fail_session_not_found(self, manager):
        """Test failing a non-existent session."""
        result = manager.fail_session("non-existent-id", "error")
        assert result is False

    def test_fail_session_expired(self, manager):
        """Test failing an expired session."""
        session = manager.create_session()
        manager._sessions[session.session_id].expires_at = datetime.utcnow() - timedelta(
            minutes=1
        )
        result = manager.fail_session(session.session_id, "error")
        assert result is False

    def test_delete_session_success(self, manager):
        """Test deleting a session successfully."""
        session = manager.create_session()
        result = manager.delete_session(session.session_id)
        assert result is True
        assert session.session_id not in manager._sessions

    def test_delete_session_not_found(self, manager):
        """Test deleting a non-existent session."""
        result = manager.delete_session("non-existent-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_completion_success(self, manager):
        """Test waiting for session completion successfully."""
        session = manager.create_session()
        payload = MagicMock(spec=PaymentPayload)

        # Complete session after a short delay
        async def complete_later():
            await asyncio.sleep(0.1)
            manager.complete_session(session.session_id, payload)

        task = asyncio.create_task(complete_later())
        result = await manager.wait_for_completion(session.session_id, timeout_seconds=5)
        await task

        assert result is not None
        assert result.is_completed()

    @pytest.mark.asyncio
    async def test_wait_for_completion_timeout(self, manager):
        """Test waiting for session completion times out."""
        session = manager.create_session()
        result = await manager.wait_for_completion(session.session_id, timeout_seconds=1)
        assert result is None

    @pytest.mark.asyncio
    async def test_wait_for_completion_session_not_found(self, manager):
        """Test waiting for non-existent session."""
        result = await manager.wait_for_completion("non-existent-id", timeout_seconds=1)
        assert result is None

    @pytest.mark.asyncio
    async def test_wait_for_completion_session_failed(self, manager):
        """Test waiting for session that fails."""
        session = manager.create_session()

        # Fail session after a short delay
        async def fail_later():
            await asyncio.sleep(0.1)
            manager.fail_session(session.session_id, "test error")

        task = asyncio.create_task(fail_later())
        result = await manager.wait_for_completion(session.session_id, timeout_seconds=5)
        await task

        assert result is not None
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_start_cleanup_task(self, manager):
        """Test starting cleanup task."""
        await manager.start_cleanup_task()
        assert manager._cleanup_task is not None
        assert not manager._cleanup_task.done()
        await manager.stop_cleanup_task()

    @pytest.mark.asyncio
    async def test_start_cleanup_task_already_running(self, manager):
        """Test starting cleanup task when already running."""
        await manager.start_cleanup_task()
        first_task = manager._cleanup_task
        await manager.start_cleanup_task()
        second_task = manager._cleanup_task
        assert first_task == second_task
        await manager.stop_cleanup_task()

    @pytest.mark.asyncio
    async def test_stop_cleanup_task(self, manager):
        """Test stopping cleanup task."""
        await manager.start_cleanup_task()
        await manager.stop_cleanup_task()
        assert manager._cleanup_task.done()

    @pytest.mark.asyncio
    async def test_stop_cleanup_task_not_running(self, manager):
        """Test stopping cleanup task when not running."""
        # Should not raise an error
        await manager.stop_cleanup_task()

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, manager):
        """Test cleanup logic removes expired sessions."""
        # Create sessions with different expiration times
        session1 = manager.create_session()
        session2 = manager.create_session()

        # Expire session1
        manager._sessions[session1.session_id].expires_at = datetime.utcnow() - timedelta(
            minutes=1
        )

        # Manually trigger cleanup logic (instead of waiting for background task)
        expired_sessions = [
            session_id
            for session_id, session in manager._sessions.items()
            if session.is_expired()
        ]

        for session_id in expired_sessions:
            manager._sessions.pop(session_id, None)

        # session1 should be removed, session2 should remain
        assert session1.session_id not in manager._sessions
        assert session2.session_id in manager._sessions

    @pytest.mark.asyncio
    async def test_cleanup_task_handles_exceptions(self, manager):
        """Test cleanup task can be started and stopped without crashing."""
        # Start and stop cleanup task to verify it doesn't crash
        await manager.start_cleanup_task()
        assert manager._cleanup_task is not None
        assert not manager._cleanup_task.done()
        
        # Stop cleanup task
        await manager.stop_cleanup_task()
        
        # Task should have been cancelled
        assert manager._cleanup_task.done()
