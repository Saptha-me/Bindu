# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We love you! - Bindu

"""Full history extraction strategy."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from bindu.utils.logging import get_logger

from ..config import MAX_FULL_HISTORY_LENGTH
from ..models import Interaction
from .base import BaseExtractionStrategy

logger = get_logger("bindu.dspy.strategies.full_history")


class FullHistoryStrategy(BaseExtractionStrategy):
    """Extract first user input and entire conversation as output.

    This strategy captures the full conversation flow, useful for training
    on complete interaction patterns.

    Usage:
        strategy = FullHistoryStrategy()
    """

    @property
    def name(self) -> str:
        return "full_history"

    def extract(
        self,
        task_id: UUID,
        messages: list[dict[str, Any]],
        feedback_score: float | None = None,
        feedback_type: str | None = None,
    ) -> Interaction | None:
        """Extract first user input and full conversation as output.

        Algorithm:
        1. Find first user message -> user_input
        2. Take all messages after it
        3. Format as "Role: content\\n..."
        4. Join with newline -> agent_output
        5. Enforce max length (drop if exceeded)
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
