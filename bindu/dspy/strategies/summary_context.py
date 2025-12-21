# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We love you! - Bindu

"""Summary context extraction strategy."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from bindu.utils.logging import get_logger

from ..models import Interaction
from .base import BaseExtractionStrategy, parse_turns

logger = get_logger("bindu.dspy.strategies.summary_context")


class SummaryContextStrategy(BaseExtractionStrategy):
    """Extract interactions with summarized conversation context.

    This strategy is designed for long conversations where including full
    context would be too large. It creates a summary of earlier turns and
    prepends it to the final user message.

    The summary is created by extracting key points from each turn:
    - For user messages: The main question or request
    - For assistant messages: The key conclusion or action taken

    Example with a 5-turn conversation:
        Turn 1: User asks about Python installation
        Turn 2: User asks about pip
        Turn 3: User asks about virtual environments
        Turn 4: User asks about packages
        Turn 5: User asks about requirements.txt

        With summary_turns=3, recent_turns=2:
        - Summarizes turns 1-3 as context
        - Includes turns 4-5 as recent context
        - Output is turn 5's agent response

    Usage:
        strategy = SummaryContextStrategy(summary_turns=5, recent_turns=2)

    Args:
        summary_turns: Number of earlier turns to summarize (default: 5)
        recent_turns: Number of recent turns to keep in full (default: 2)
        max_summary_length: Maximum character length for summary (default: 500)
        summary_format: Format style - "bullets" or "paragraph" (default: "bullets")
    """

    def __init__(
        self,
        summary_turns: int = 5,
        recent_turns: int = 2,
        max_summary_length: int = 500,
        summary_format: str = "bullets",
    ):
        self.summary_turns = max(1, summary_turns)
        self.recent_turns = max(1, recent_turns)
        self.max_summary_length = max(100, max_summary_length)
        self.summary_format = summary_format if summary_format in ("bullets", "paragraph") else "bullets"

    @property
    def name(self) -> str:
        return "summary_context"

    def extract(
        self,
        task_id: UUID,
        messages: list[dict[str, Any]],
        feedback_score: float | None = None,
        feedback_type: str | None = None,
    ) -> Interaction | None:
        """Extract interaction with summarized earlier context.

        Algorithm:
        1. Parse messages into turns
        2. Split into summary_turns (to summarize) and recent_turns (to keep full)
        3. Create summary of earlier turns
        4. Combine summary + recent user context as user_input
        5. Use last agent response as agent_output
        """
        turns = parse_turns(messages)

        if not turns:
            logger.debug(f"Task {task_id}: No complete turns found in history")
            return None

        # If we have fewer turns than recent_turns, just use all turns without summary
        if len(turns) <= self.recent_turns:
            return self._create_simple_interaction(task_id, turns, feedback_score, feedback_type)

        # Split turns into summary portion and recent portion
        total_context_turns = self.summary_turns + self.recent_turns
        if len(turns) <= total_context_turns:
            # Not enough turns to need summarization, use available turns
            split_point = max(0, len(turns) - self.recent_turns)
            turns_to_summarize = turns[:split_point]
            recent_context = turns[split_point:]
        else:
            # Take the relevant window from the end
            relevant_turns = turns[-total_context_turns:]
            turns_to_summarize = relevant_turns[:self.summary_turns]
            recent_context = relevant_turns[self.summary_turns:]

        # Create summary of earlier turns
        summary = self._create_summary(turns_to_summarize)

        # Format recent turns
        recent_formatted = self._format_recent_turns(recent_context)

        # Combine summary with recent context
        if summary:
            user_input = f"[Previous conversation summary]\n{summary}\n\n[Recent conversation]\n{recent_formatted}"
        else:
            user_input = recent_formatted

        # Get last agent response as output
        agent_output = turns[-1][1]

        if not user_input or not agent_output:
            logger.debug(
                f"Task {task_id}: Could not extract summary context "
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

    def _create_summary(self, turns: list[tuple[str, str]]) -> str:
        """Create a summary of conversation turns.

        Args:
            turns: List of (user_content, assistant_content) tuples

        Returns:
            Summarized string representation
        """
        if not turns:
            return ""

        if self.summary_format == "bullets":
            return self._create_bullet_summary(turns)
        else:
            return self._create_paragraph_summary(turns)

    def _create_bullet_summary(self, turns: list[tuple[str, str]]) -> str:
        """Create bullet-point summary of turns."""
        bullets = []

        for i, (user_msg, assistant_msg) in enumerate(turns, 1):
            # Extract key point from user message (first sentence or truncated)
            user_key = self._extract_key_point(user_msg, prefix="Asked")
            # Extract key point from assistant response
            assistant_key = self._extract_key_point(assistant_msg, prefix="Answered")

            bullets.append(f"- Turn {i}: {user_key}; {assistant_key}")

        summary = "\n".join(bullets)

        # Truncate if too long
        if len(summary) > self.max_summary_length:
            summary = summary[:self.max_summary_length - 3] + "..."

        return summary

    def _create_paragraph_summary(self, turns: list[tuple[str, str]]) -> str:
        """Create paragraph-style summary of turns."""
        points = []

        for user_msg, assistant_msg in turns:
            user_key = self._extract_key_point(user_msg, prefix="User asked about")
            assistant_key = self._extract_key_point(assistant_msg, prefix="and received information on")
            points.append(f"{user_key} {assistant_key}.")

        summary = " ".join(points)

        # Truncate if too long
        if len(summary) > self.max_summary_length:
            summary = summary[:self.max_summary_length - 3] + "..."

        return summary

    def _extract_key_point(self, text: str, prefix: str = "") -> str:
        """Extract key point from text (first sentence or truncated).

        Args:
            text: Full text to extract from
            prefix: Optional prefix to add

        Returns:
            Key point string
        """
        # Clean whitespace
        text = " ".join(text.split())

        # Try to get first sentence
        sentence_end = -1
        for end_char in ".!?":
            pos = text.find(end_char)
            if pos != -1:
                if sentence_end == -1 or pos < sentence_end:
                    sentence_end = pos

        if sentence_end != -1 and sentence_end < 100:
            key_point = text[:sentence_end + 1]
        else:
            # Truncate to reasonable length
            if len(text) > 80:
                # Try to break at word boundary
                key_point = text[:80].rsplit(" ", 1)[0] + "..."
            else:
                key_point = text

        if prefix:
            return f"{prefix}: {key_point}"
        return key_point

    def _format_recent_turns(self, turns: list[tuple[str, str]]) -> str:
        """Format recent turns as full context.

        Args:
            turns: List of recent (user_content, assistant_content) tuples

        Returns:
            Formatted string with recent conversation
        """
        if not turns:
            return ""

        if len(turns) == 1:
            return turns[0][0]

        # Format with role labels for clarity
        lines = []
        for user_msg, assistant_msg in turns[:-1]:
            lines.append(f"User: {user_msg}")
            lines.append(f"Assistant: {assistant_msg}")

        # Add final user message (the one we're getting a response to)
        lines.append(f"User: {turns[-1][0]}")

        return "\n".join(lines)

    def _create_simple_interaction(
        self,
        task_id: UUID,
        turns: list[tuple[str, str]],
        feedback_score: float | None,
        feedback_type: str | None,
    ) -> Interaction | None:
        """Create interaction when no summarization is needed.

        Args:
            task_id: The task ID
            turns: All turns (fewer than recent_turns)
            feedback_score: Normalized feedback score
            feedback_type: Type of feedback

        Returns:
            Interaction or None
        """
        if not turns:
            return None

        if len(turns) == 1:
            user_input = turns[0][0]
        else:
            user_input = self._format_recent_turns(turns)

        agent_output = turns[-1][1]

        if not user_input or not agent_output:
            return None

        return Interaction(
            id=task_id,
            user_input=user_input,
            agent_output=agent_output,
            feedback_score=feedback_score,
            feedback_type=feedback_type,
        )
