# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We love you! - Bindu

"""Base extraction strategy and shared utilities.

This module provides the abstract base class for all extraction strategies
and shared utility functions like parse_turns.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from bindu.utils.logging import get_logger

from ..models import Interaction

logger = get_logger("bindu.dspy.strategies")


def parse_turns(messages: list[dict[str, Any]]) -> list[tuple[str, str]]:
    """Parse messages into (user, assistant) turn pairs.

    This is a shared utility function used by multi-turn strategies.

    Args:
        messages: Cleaned message history

    Returns:
        List of (user_content, assistant_content) tuples
    """
    turns: list[tuple[str, str]] = []
    i = 0

    while i < len(messages):
        msg = messages[i]
        role = msg.get("role", "").lower()

        if role == "user":
            user_content = msg.get("content", "")
            # Look for following assistant message
            assistant_content = None
            for j in range(i + 1, len(messages)):
                next_msg = messages[j]
                next_role = next_msg.get("role", "").lower()
                if next_role in ("assistant", "agent"):
                    assistant_content = next_msg.get("content", "")
                    i = j + 1
                    break
                elif next_role == "user":
                    # No assistant response for this user message
                    break

            if assistant_content:
                turns.append((user_content, assistant_content))
            else:
                i += 1
        else:
            i += 1

    return turns


class BaseExtractionStrategy(ABC):
    """Abstract base class for extraction strategies.

    Each strategy encapsulates its own configuration and extraction logic.
    Subclasses define their own __init__ with only the parameters they need.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the strategy name for logging and identification."""
        pass

    @abstractmethod
    def extract(
        self,
        task_id: UUID,
        messages: list[dict[str, Any]],
        feedback_score: float | None = None,
        feedback_type: str | None = None,
    ) -> Interaction | None:
        """Extract an interaction from cleaned messages.

        Args:
            task_id: The task ID
            messages: Cleaned message history (already validated, non-empty content)
            feedback_score: Normalized feedback score [0.0, 1.0]
            feedback_type: Type of feedback

        Returns:
            Interaction object or None if extraction fails
        """
        pass

    def extract_all(
        self,
        task_id: UUID,
        messages: list[dict[str, Any]],
        feedback_score: float | None = None,
        feedback_type: str | None = None,
    ) -> list[Interaction]:
        """Extract all interactions from cleaned messages.

        This method supports strategies that produce multiple interactions
        from a single conversation (e.g., SlidingWindowStrategy).

        The default implementation wraps extract() for single-interaction strategies.

        Args:
            task_id: The task ID
            messages: Cleaned message history (already validated, non-empty content)
            feedback_score: Normalized feedback score [0.0, 1.0]
            feedback_type: Type of feedback

        Returns:
            List of Interaction objects (may be empty if extraction fails)
        """
        result = self.extract(task_id, messages, feedback_score, feedback_type)
        return [result] if result else []
