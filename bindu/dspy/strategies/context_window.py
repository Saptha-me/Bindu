# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We love you! - Bindu

"""Context window extraction strategy."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from bindu.utils.logging import get_logger

from ..config import DEFAULT_N_TURNS
from ..models import Interaction
from .base import BaseExtractionStrategy, parse_turns

logger = get_logger("bindu.dspy.strategies.context_window")


class ContextWindowStrategy(BaseExtractionStrategy):
    """Extract last N turns with concatenated user messages as input.

    This strategy balances context preservation with conciseness by:
    - Providing multi-turn user context for understanding conversation flow
    - Focusing on the final agent response as the training target
    - Optionally including a system prompt for prompt optimization

    Usage:
        strategy = ContextWindowStrategy(n_turns=3, system_prompt="You are helpful.")

    Args:
        n_turns: Number of turns to extract (default: 3, minimum: 1)
        system_prompt: Optional system prompt to include in extracted interactions
    """

    def __init__(
        self,
        n_turns: int = DEFAULT_N_TURNS,
        system_prompt: str | None = None,
    ):
        self.n_turns = max(1, n_turns)
        self.system_prompt = system_prompt

    @property
    def name(self) -> str:
        return "context_window"

    def extract(
        self,
        task_id: UUID,
        messages: list[dict[str, Any]],
        feedback_score: float | None = None,
        feedback_type: str | None = None,
    ) -> Interaction | None:
        """Extract last N turns with concatenated user messages as input.

        Algorithm:
        1. Parse messages into (user, assistant) turn pairs
        2. Take last N turns
        3. Concatenate all user messages as user_input
        4. Use last agent response as agent_output
        5. Include system_prompt if provided
        """
        turns = parse_turns(messages)

        if not turns:
            logger.debug(f"Task {task_id}: No complete turns found in history")
            return None

        # Take last N turns
        selected_turns = turns[-self.n_turns :]

        # Get the last agent response as output
        agent_output = selected_turns[-1][1]

        # Concatenate user messages from selected turns
        user_messages = [turn[0] for turn in selected_turns]

        if len(user_messages) == 1:
            user_input = user_messages[0]
        else:
            # Format with turn indicators for clarity
            formatted_messages = []
            for i, msg in enumerate(user_messages, 1):
                if len(user_messages) <= 3:
                    # For small windows, use simple separator
                    formatted_messages.append(msg)
                else:
                    # For larger windows, add turn numbers
                    formatted_messages.append(f"[Turn {i}] {msg}")

            user_input = "\n\n".join(formatted_messages)

        if not user_input or not agent_output:
            logger.debug(
                f"Task {task_id}: Could not extract context window "
                f"(user_input={bool(user_input)}, agent_output={bool(agent_output)})"
            )
            return None

        return Interaction(
            id=task_id,
            user_input=user_input,
            agent_output=agent_output,
            feedback_score=feedback_score,
            feedback_type=feedback_type,
            system_prompt=self.system_prompt,
        )
