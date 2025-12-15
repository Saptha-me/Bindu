# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Interaction extraction strategies for DSPy training data.

This module provides different strategies for extracting user-agent interactions
from task history. Each strategy determines how to identify the user input and
agent output from a sequence of messages.
"""

from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from bindu.utils.logging import get_logger

from .config import MAX_FULL_HISTORY_LENGTH
from .models import Interaction

logger = get_logger("bindu.dspy.extractor")


class ExtractionStrategy(str, Enum):
    """Strategies for extracting interactions from task history."""

    LAST_TURN = "last_turn"
    """Extract only the last user-assistant turn from history."""

    FULL_HISTORY = "full_history"
    """Extract first user input and entire conversation as output."""


class InteractionExtractor:
    """Extracts interactions from task history using different strategies."""

    def __init__(self, strategy: ExtractionStrategy = ExtractionStrategy.LAST_TURN):
        """Initialize the extractor with a specific strategy.

        Args:
            strategy: The extraction strategy to use
        """
        self.strategy = strategy
        logger.info(f"Initialized InteractionExtractor with strategy: {strategy.value}")

    def extract(
        self,
        task_id: UUID,
        history: list[dict[str, Any]],
        feedback_score: float | None = None,
        feedback_type: str | None = None,
    ) -> Interaction | None:
        """Extract an interaction from task history.

        Args:
            task_id: The task ID
            history: The task history (list of messages)
            feedback_score: Normalized feedback score [0.0, 1.0]
            feedback_type: Type of feedback

        Returns:
            Interaction object or None if extraction fails
        """
        # Validate history
        if not isinstance(history, list) or not history:
            logger.debug(f"Task {task_id}: Empty or invalid history")
            return None

        # Clean messages - drop empty content
        messages = self._clean_messages(history)
        if not messages:
            logger.debug(f"Task {task_id}: No valid messages after cleaning")
            return None

        # Extract based on strategy
        if self.strategy == ExtractionStrategy.LAST_TURN:
            return self._extract_last_turn(task_id, messages, feedback_score, feedback_type)
        elif self.strategy == ExtractionStrategy.FULL_HISTORY:
            return self._extract_full_history(task_id, messages, feedback_score, feedback_type)
        else:
            logger.error(f"Unknown extraction strategy: {self.strategy}")
            return None

    def _clean_messages(self, history: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Clean messages by removing those with empty content.

        Args:
            history: Raw message history

        Returns:
            Cleaned list of messages
        """
        cleaned = []
        for msg in history:
            if not isinstance(msg, dict):
                continue

            role = msg.get("role")
            content = msg.get("content", "")

            # Skip if no role or empty content
            if not role or not content or not str(content).strip():
                continue

            cleaned.append({"role": role, "content": str(content).strip()})

        return cleaned

    def _extract_last_turn(
        self,
        task_id: UUID,
        messages: list[dict[str, Any]],
        feedback_score: float | None,
        feedback_type: str | None,
    ) -> Interaction | None:
        """Extract the last user-assistant turn.

        Algorithm:
        1. Traverse history from end
        2. Find last assistant message → agent_output
        3. Find nearest preceding user message → user_input
        4. If either missing → drop task

        Args:
            task_id: The task ID
            messages: Cleaned message history
            feedback_score: Normalized feedback score
            feedback_type: Type of feedback

        Returns:
            Interaction object or None
        """
        agent_output = None
        user_input = None

        # Traverse from end to find last assistant message
        for i in range(len(messages) - 1, -1, -1):
            msg = messages[i]
            role = msg.get("role", "").lower()

            if role in ("assistant", "agent") and not agent_output:
                agent_output = msg.get("content")
                # Now find preceding user message
                for j in range(i - 1, -1, -1):
                    prev_msg = messages[j]
                    prev_role = prev_msg.get("role", "").lower()
                    if prev_role == "user":
                        user_input = prev_msg.get("content")
                        break
                break

        # Validate extraction
        if not user_input or not agent_output:
            logger.debug(
                f"Task {task_id}: Could not extract last turn "
                f"(user_input={bool(user_input)}, agent_output={bool(agent_output)})"
            )
            return None

        return Interaction(
            id=task_id,
            user_input=user_input,
            agent_output=agent_output,
            feedback_score=feedback_score,
            feedback_type=feedback_type,
        )

    def _extract_full_history(
        self,
        task_id: UUID,
        messages: list[dict[str, Any]],
        feedback_score: float | None,
        feedback_type: str | None,
    ) -> Interaction | None:
        """Extract first user input and full conversation as output.

        Algorithm:
        1. Find first user message → user_input
        2. Take all messages after it
        3. Format as "Role: content\\n..."
        4. Join with newline → agent_output
        5. Enforce max length (drop if exceeded)

        Args:
            task_id: The task ID
            messages: Cleaned message history
            feedback_score: Normalized feedback score
            feedback_type: Type of feedback

        Returns:
            Interaction object or None
        """
        # Find first user message
        user_input = None
        first_user_idx = -1

        for i, msg in enumerate(messages):
            role = msg.get("role", "").lower()
            if role == "user":
                user_input = msg.get("content")
                first_user_idx = i
                break

        if not user_input or first_user_idx == -1:
            logger.debug(f"Task {task_id}: No user message found in history")
            return None

        # Take all messages after first user message
        remaining_messages = messages[first_user_idx + 1 :]
        if not remaining_messages:
            logger.debug(f"Task {task_id}: No messages after first user input")
            return None

        # Format messages
        formatted_lines = []
        for msg in remaining_messages:
            role = msg.get("role", "").capitalize()
            content = msg.get("content", "")
            formatted_lines.append(f"{role}: {content}")

        agent_output = "\n".join(formatted_lines)

        # Enforce max length
        if len(agent_output) > MAX_FULL_HISTORY_LENGTH:
            logger.debug(
                f"Task {task_id}: Full history exceeds max length "
                f"({len(agent_output)} > {MAX_FULL_HISTORY_LENGTH})"
            )
            return None

        return Interaction(
            id=task_id,
            user_input=user_input,
            agent_output=agent_output,
            feedback_score=feedback_score,
            feedback_type=feedback_type,
        )
