# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We love you! - Bindu

"""Last turn extraction strategy."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from bindu.utils.logging import get_logger

from ..models import Interaction
from .base import BaseExtractionStrategy

logger = get_logger("bindu.dspy.strategies.last_turn")


class LastTurnStrategy(BaseExtractionStrategy):
    """Extract only the last user-assistant turn from history.

    This is the simplest strategy - it finds the last complete user-assistant
    exchange and uses that as the training example.

    Usage:
        strategy = LastTurnStrategy()
    """

    @property
    def name(self) -> str:
        return "last_turn"

    def extract(
        self,
        task_id: UUID,
        messages: list[dict[str, Any]],
        feedback_score: float | None = None,
        feedback_type: str | None = None,
    ) -> Interaction | None:
        """Extract the last user-assistant turn.

        Algorithm:
        1. Traverse history from end
        2. Find last assistant message -> agent_output
        3. Find nearest preceding user message -> user_input
        4. If either missing -> return None
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
