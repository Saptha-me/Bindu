# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We love you! - Bindu

"""Last N turns extraction strategy."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from bindu.utils.logging import get_logger

from ..config import DEFAULT_N_TURNS
from ..models import Interaction
from .base import BaseExtractionStrategy, parse_turns

logger = get_logger("bindu.dspy.strategies.last_n_turns")


class LastNTurnsStrategy(BaseExtractionStrategy):
    """Extract the last N user-assistant turns.

    This strategy formats earlier turns as context prepended to the final
    user message, with the last assistant response as the output.

    Usage:
        strategy = LastNTurnsStrategy(n_turns=3)

    Args:
        n_turns: Number of turns to extract (default: 3, minimum: 1)
    """

    def __init__(self, n_turns: int = DEFAULT_N_TURNS):
        self.n_turns = max(1, n_turns)

    @property
    def name(self) -> str:
        return "last_n_turns"

    def extract(
        self,
        task_id: UUID,
        messages: list[dict[str, Any]],
        feedback_score: float | None = None,
        feedback_type: str | None = None,
    ) -> Interaction | None:
        """Extract the last N user-assistant turns.

        Algorithm:
        1. Parse messages into (user, assistant) turn pairs
        2. Take last N turns
        3. Format earlier turns as context: "User: ...\\nAssistant: ..."
        4. Use last user message as user_input
        5. Use last assistant message as agent_output
        6. Prepend context to user_input if multiple turns
        """
        turns = parse_turns(messages)

        if not turns:
            logger.debug(f"Task {task_id}: No complete turns found in history")
            return None

        # Take last N turns
        selected_turns = turns[-self.n_turns :]

        if len(selected_turns) == 1:
            user_input, agent_output = selected_turns[0]
        else:
            # Multiple turns - format context + final turn
            context_lines = []
            for user_msg, assistant_msg in selected_turns[:-1]:
                context_lines.append(f"User: {user_msg}")
                context_lines.append(f"Assistant: {assistant_msg}")

            context = "\n".join(context_lines)
            final_user, agent_output = selected_turns[-1]
            user_input = f"{context}\n\nUser: {final_user}"

        if not user_input or not agent_output:
            logger.debug(
                f"Task {task_id}: Could not extract last {self.n_turns} turns "
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
