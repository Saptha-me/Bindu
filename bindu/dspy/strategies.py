# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Extraction strategies for DSPy training data.

This module provides different strategies for extracting user-agent interactions
from task history. Each strategy is a self-contained class with its own
configuration parameters.

Usage:
    # Simple strategies - no config needed
    strategy = LastTurnStrategy()

    # Strategies with config - params in constructor
    strategy = ContextWindowStrategy(n_turns=3, system_prompt="You are helpful.")

    # Factory approach
    strategy = get_strategy("context_window", n_turns=3, system_prompt="You are helpful.")
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

from bindu.utils.logging import get_logger

from .config import DEFAULT_N_TURNS, DEFAULT_STRIDE, DEFAULT_WINDOW_SIZE, MAX_FULL_HISTORY_LENGTH
from .models import Interaction

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


# Strategy registry for factory pattern
STRATEGIES: dict[str, type[BaseExtractionStrategy]] = {
    "last_turn": LastTurnStrategy,
    "full_history": FullHistoryStrategy,
    "last_n_turns": LastNTurnsStrategy,
    "first_n_turns": FirstNTurnsStrategy,
    "context_window": ContextWindowStrategy,
    "sliding_window": SlidingWindowStrategy,
    "summary_context": SummaryContextStrategy,
}


def get_strategy(name: str, **kwargs: Any) -> BaseExtractionStrategy:
    """Factory function to create a strategy by name.

    Args:
        name: Strategy name (e.g., "last_turn", "context_window")
        **kwargs: Strategy-specific configuration parameters

    Returns:
        Configured strategy instance

    Raises:
        ValueError: If strategy name is not recognized

    Examples:
        >>> strategy = get_strategy("last_turn")
        >>> strategy = get_strategy("context_window", n_turns=5, system_prompt="Be helpful")
    """
    if name not in STRATEGIES:
        available = ", ".join(STRATEGIES.keys())
        raise ValueError(f"Unknown strategy: {name}. Available: {available}")

    strategy_class = STRATEGIES[name]
    return strategy_class(**kwargs)
