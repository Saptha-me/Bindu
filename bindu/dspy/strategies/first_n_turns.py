# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We love you! - Bindu

"""First N turns extraction strategy."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from bindu.utils.logging import get_logger

from ..config import DEFAULT_N_TURNS
from ..models import Interaction
from .base import BaseExtractionStrategy, parse_turns

logger = get_logger("bindu.dspy.strategies.first_n_turns")


class FirstNTurnsStrategy(BaseExtractionStrategy):
    """Extract the first N user-assistant turns from history.

    This strategy uses the first user message as input and formats the
    subsequent conversation as the output.

    Usage:
        strategy = FirstNTurnsStrategy(n_turns=3)

    Args:
        n_turns: Number of turns to extract (default: 3, minimum: 1)
    """

    def __init__(self, n_turns: int = DEFAULT_N_TURNS):
        self.n_turns = max(1, n_turns)

    @property
    def name(self) -> str:
        return "first_n_turns"

    def extract(
        self,
        task_id: UUID,
        messages: list[dict[str, Any]],
        feedback_score: float | None = None,
        feedback_type: str | None = None,
    ) -> Interaction | None:
        """Extract the first N user-assistant turns.

        Algorithm:
        1. Parse messages into (user, assistant) turn pairs
        2. Take first N turns
        3. Use first user message as user_input
        4. Format all assistant responses (with interleaved user context) as agent_output
        """
        turns = parse_turns(messages)

        if not turns:
            logger.debug(f"Task {task_id}: No complete turns found in history")
            return None

        # Take first N turns
        selected_turns = turns[: self.n_turns]

        # First user message is the input
        user_input = selected_turns[0][0]

        if len(selected_turns) == 1:
            agent_output = selected_turns[0][1]
        else:
            # Multiple turns - format as conversation output
            output_lines = []
            output_lines.append(f"Assistant: {selected_turns[0][1]}")

            for user_msg, assistant_msg in selected_turns[1:]:
                output_lines.append(f"User: {user_msg}")
                output_lines.append(f"Assistant: {assistant_msg}")

            agent_output = "\n".join(output_lines)

        if not user_input or not agent_output:
            logger.debug(
                f"Task {task_id}: Could not extract first {self.n_turns} turns "
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
