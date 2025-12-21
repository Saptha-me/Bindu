# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We love you! - Bindu

"""Sliding window extraction strategy."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from bindu.utils.logging import get_logger

from ..config import DEFAULT_STRIDE, DEFAULT_WINDOW_SIZE
from ..models import Interaction
from .base import BaseExtractionStrategy, parse_turns

logger = get_logger("bindu.dspy.strategies.sliding_window")


class SlidingWindowStrategy(BaseExtractionStrategy):
    """Extract multiple training examples from a single conversation using sliding windows.

    This strategy generates multiple (user_input, agent_output) pairs by sliding
    a window across the conversation. This multiplies your training data, which
    benefits DSPy optimizers like MIPRO and BootstrapFewShot.

    Example with window_size=2, stride=1 on a 4-turn conversation:
        Turn 1: User1 -> Agent1
        Turn 2: User2 -> Agent2
        Turn 3: User3 -> Agent3
        Turn 4: User4 -> Agent4

        Produces 3 examples:
        - Example 1: (User1, User2) -> Agent2
        - Example 2: (User2, User3) -> Agent3
        - Example 3: (User3, User4) -> Agent4

    Example with start_offset=1:
        Produces 2 examples (skips first turn):
        - Example 1: (User2, User3) -> Agent3
        - Example 2: (User3, User4) -> Agent4

    Usage:
        strategy = SlidingWindowStrategy(window_size=2, stride=1)
        strategy = SlidingWindowStrategy(window_size=2, stride=1, start_offset=1)

    Args:
        window_size: Number of turns per window (default: 2, minimum: 1)
        stride: How many turns to slide forward (default: 1)
            - stride=1: Overlapping windows (more examples)
            - stride=window_size: Non-overlapping windows
        start_offset: Starting position in turns to begin sliding (default: 0)
            - start_offset=0: Start from the beginning
            - start_offset=N: Skip first N turns
    """

    def __init__(
        self,
        window_size: int = DEFAULT_WINDOW_SIZE,
        stride: int = DEFAULT_STRIDE,
        start_offset: int = 0,
    ):
        self.window_size = max(1, window_size)
        self.stride = max(1, stride)
        self.start_offset = max(0, start_offset)

    @property
    def name(self) -> str:
        return "sliding_window"

    def extract(
        self,
        task_id: UUID,
        messages: list[dict[str, Any]],
        feedback_score: float | None = None,
        feedback_type: str | None = None,
    ) -> Interaction | None:
        """Extract a single interaction (last window).

        For single extraction, behaves like ContextWindowStrategy with window_size turns.
        For multiple extractions, use extract_all().
        """
        turns = parse_turns(messages)

        if len(turns) < self.window_size:
            logger.debug(
                f"Task {task_id}: Not enough turns for window "
                f"({len(turns)} < {self.window_size})"
            )
            return None

        # Take the last window
        window = turns[-self.window_size:]
        return self._create_interaction_from_window(
            task_id, window, feedback_score, feedback_type
        )

    def extract_all(
        self,
        task_id: UUID,
        messages: list[dict[str, Any]],
        feedback_score: float | None = None,
        feedback_type: str | None = None,
    ) -> list[Interaction]:
        """Extract multiple interactions using sliding windows.

        Slides a window of size `window_size` across the conversation,
        moving `stride` turns at a time. Optionally starts from `start_offset`.
        """
        turns = parse_turns(messages)

        # Check if we have enough turns considering the offset
        effective_start = min(self.start_offset, len(turns))
        if len(turns) - effective_start < self.window_size:
            logger.debug(
                f"Task {task_id}: Not enough turns for sliding window after offset "
                f"(available={len(turns) - effective_start}, required={self.window_size})"
            )
            return []

        interactions: list[Interaction] = []

        # Slide the window across turns, starting from start_offset
        for start_idx in range(effective_start, len(turns) - self.window_size + 1, self.stride):
            window = turns[start_idx : start_idx + self.window_size]
            interaction = self._create_interaction_from_window(
                task_id, window, feedback_score, feedback_type
            )
            if interaction:
                interactions.append(interaction)

        logger.debug(
            f"Task {task_id}: Extracted {len(interactions)} interactions "
            f"with sliding window (size={self.window_size}, stride={self.stride}, offset={self.start_offset})"
        )
        return interactions

    def _create_interaction_from_window(
        self,
        task_id: UUID,
        window: list[tuple[str, str]],
        feedback_score: float | None,
        feedback_type: str | None,
    ) -> Interaction | None:
        """Create an Interaction from a window of turns.

        Args:
            task_id: The task ID
            window: List of (user_content, assistant_content) tuples
            feedback_score: Normalized feedback score
            feedback_type: Type of feedback

        Returns:
            Interaction object or None if creation fails
        """
        if not window:
            return None

        # Get the last agent response as output
        agent_output = window[-1][1]

        # Concatenate user messages from window
        user_messages = [turn[0] for turn in window]

        if len(user_messages) == 1:
            user_input = user_messages[0]
        else:
            # Format with context for clarity
            if len(user_messages) <= 3:
                user_input = "\n\n".join(user_messages)
            else:
                formatted = [f"[Turn {i+1}] {msg}" for i, msg in enumerate(user_messages)]
                user_input = "\n\n".join(formatted)

        if not user_input or not agent_output:
            return None

        # Create unique ID for each window by combining task_id with window_index
        # We use the same task_id but the deduplication in dataset.py will handle
        # duplicates based on (user_input, agent_output) content
        return Interaction(
            id=task_id,
            user_input=user_input,
            agent_output=agent_output,
            feedback_score=feedback_score,
            feedback_type=feedback_type,
        )
