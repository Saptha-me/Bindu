# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Payment Session Manager for x402 payment flow.

Manages payment sessions where users can:
1. Start a payment session
2. Complete payment in browser
3. Retrieve payment token without consuming it
"""

from __future__ import annotations

import asyncio
import secrets
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, field

from x402.types import PaymentPayload

from bindu.utils.logging import get_logger

logger = get_logger("bindu.server.middleware.x402.payment_session")


@dataclass
class PaymentSession:
    """Represents a payment session."""

    session_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(
        default_factory=lambda: datetime.utcnow() + timedelta(minutes=15)
    )
    payment_payload: Optional[PaymentPayload] = None
    status: str = "pending"  # pending, completed, expired, failed
    error: Optional[str] = None

    def is_expired(self) -> bool:
        """Check if session has expired."""
        return datetime.utcnow() > self.expires_at

    def is_completed(self) -> bool:
        """Check if payment is completed."""
        return self.status == "completed" and self.payment_payload is not None


class PaymentSessionManager:
    """Manages payment sessions for x402 payment flow."""

    def __init__(self, session_timeout_minutes: int = 15):
        """Initialize payment session manager.

        Args:
            session_timeout_minutes: Session timeout in minutes (default: 15)
        """
        self._sessions: dict[str, PaymentSession] = {}
        self._session_timeout = timedelta(minutes=session_timeout_minutes)
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup_task(self) -> None:
        """Start background task to cleanup expired sessions."""
        if self._cleanup_task is None or self._cleanup_task.done():
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_sessions())
            logger.info("Payment session cleanup task started")

    async def stop_cleanup_task(self) -> None:
        """Stop background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Payment session cleanup task stopped")

    async def _cleanup_expired_sessions(self) -> None:
        """Background task to cleanup expired sessions every minute."""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                expired_sessions = [
                    session_id
                    for session_id, session in self._sessions.items()
                    if session.is_expired()
                ]

                for session_id in expired_sessions:
                    session = self._sessions.pop(session_id, None)
                    if session:
                        logger.info(f"Cleaned up expired session: {session_id}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}", exc_info=True)

    def create_session(self) -> PaymentSession:
        """Create a new payment session.

        Returns:
            PaymentSession: New payment session
        """
        session_id = secrets.token_urlsafe(32)
        session = PaymentSession(session_id=session_id)
        self._sessions[session_id] = session

        logger.info(f"Created payment session: {session_id}")
        return session

    def get_session(self, session_id: str) -> Optional[PaymentSession]:
        """Get payment session by ID.

        Args:
            session_id: Session ID

        Returns:
            PaymentSession if found and not expired, None otherwise
        """
        session = self._sessions.get(session_id)

        if session is None:
            return None

        if session.is_expired():
            # Mark as expired and remove
            session.status = "expired"
            self._sessions.pop(session_id, None)
            logger.info(f"Session expired: {session_id}")
            return None

        return session

    def complete_session(
        self, session_id: str, payment_payload: PaymentPayload
    ) -> bool:
        """Mark session as completed with payment payload.

        Args:
            session_id: Session ID
            payment_payload: Payment payload from x402

        Returns:
            True if session was completed successfully, False otherwise
        """
        session = self.get_session(session_id)

        if session is None:
            logger.warning(
                f"Cannot complete session: not found or expired: {session_id}"
            )
            return False

        session.payment_payload = payment_payload
        session.status = "completed"

        logger.info(f"Payment session completed: {session_id}")
        return True

    def fail_session(self, session_id: str, error: str) -> bool:
        """Mark session as failed.

        Args:
            session_id: Session ID
            error: Error message

        Returns:
            True if session was marked as failed, False if not found
        """
        session = self.get_session(session_id)

        if session is None:
            logger.warning(f"Cannot fail session: not found or expired: {session_id}")
            return False

        session.status = "failed"
        session.error = error

        logger.warning(f"Payment session failed: {session_id} - {error}")
        return True

    async def wait_for_completion(
        self, session_id: str, timeout_seconds: int = 300
    ) -> Optional[PaymentSession]:
        """Wait for session to complete (polling).

        Args:
            session_id: Session ID
            timeout_seconds: Maximum time to wait in seconds (default: 300)

        Returns:
            PaymentSession if completed, None if timeout or error
        """
        start_time = datetime.utcnow()
        timeout = timedelta(seconds=timeout_seconds)

        while datetime.utcnow() - start_time < timeout:
            session = self.get_session(session_id)

            if session is None:
                logger.warning(
                    f"Session not found or expired during wait: {session_id}"
                )
                return None

            if session.is_completed():
                logger.info(f"Session completed during wait: {session_id}")
                return session

            if session.status == "failed":
                logger.warning(f"Session failed during wait: {session_id}")
                return session

            # Poll every second
            await asyncio.sleep(1)

        logger.warning(f"Timeout waiting for session: {session_id}")
        return None

    def delete_session(self, session_id: str) -> bool:
        """Delete a session.

        Args:
            session_id: Session ID

        Returns:
            True if session was deleted, False if not found
        """
        session = self._sessions.pop(session_id, None)
        if session:
            logger.info(f"Deleted payment session: {session_id}")
            return True
        return False
