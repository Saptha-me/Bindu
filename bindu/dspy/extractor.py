# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Interaction extractor for DSPy training data.

This module provides the InteractionExtractor class that orchestrates
message cleaning and delegates extraction to strategy classes.

For strategy implementations, see the strategies module.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from bindu.utils.logging import get_logger

from .models import Interaction
from .strategies import BaseExtractionStrategy, LastTurnStrategy

logger = get_logger("bindu.dspy.extractor")


def clean_messages(history: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


class InteractionExtractor:
    """Extracts interactions from task history using pluggable strategies.

    The extractor handles message validation and cleaning, then delegates
    the actual extraction logic to the provided strategy.

    Usage:
        # With default strategy (LastTurnStrategy)
        extractor = InteractionExtractor()

        # With custom strategy
        from bindu.dspy.strategies import ContextWindowStrategy
        strategy = ContextWindowStrategy(n_turns=3, system_prompt="Be helpful")
        extractor = InteractionExtractor(strategy)

        # Extract interaction
        interaction = extractor.extract(task_id, history, feedback_score, feedback_type)
    """

    def __init__(self, strategy: BaseExtractionStrategy | None = None):
        """Initialize the extractor with a strategy.

        Args:
            strategy: Extraction strategy to use. Defaults to LastTurnStrategy.
        """
        self.strategy = strategy or LastTurnStrategy()
        logger.info(f"Initialized InteractionExtractor with strategy: {self.strategy.name}")

    def extract(
        self,
        task_id: UUID,
        history: list[dict[str, Any]],
        feedback_score: float | None = None,
        feedback_type: str | None = None,
    ) -> Interaction | None:
        """Extract a single interaction from task history.

        Args:
            task_id: The task ID
            history: The task history (list of messages)
            feedback_score: Normalized feedback score [0.0, 1.0]
            feedback_type: Type of feedback

        Returns:
            Interaction object or None if extraction fails
        """
        messages = self._validate_and_clean(task_id, history)
        if not messages:
            return None

        # Delegate to strategy
        return self.strategy.extract(task_id, messages, feedback_score, feedback_type)

    def extract_all(
        self,
        task_id: UUID,
        history: list[dict[str, Any]],
        feedback_score: float | None = None,
        feedback_type: str | None = None,
    ) -> list[Interaction]:
        """Extract all interactions from task history.

        This method supports strategies that produce multiple interactions
        from a single conversation (e.g., SlidingWindowStrategy).

        For single-interaction strategies, this returns a list with one element.

        Args:
            task_id: The task ID
            history: The task history (list of messages)
            feedback_score: Normalized feedback score [0.0, 1.0]
            feedback_type: Type of feedback

        Returns:
            List of Interaction objects (may be empty if extraction fails)
        """
        messages = self._validate_and_clean(task_id, history)
        if not messages:
            return []

        # Delegate to strategy's extract_all
        return self.strategy.extract_all(task_id, messages, feedback_score, feedback_type)

    def _validate_and_clean(
        self,
        task_id: UUID,
        history: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Validate history and clean messages.

        Args:
            task_id: The task ID
            history: The task history (list of messages)

        Returns:
            Cleaned messages or empty list if validation fails
        """
        # Validate history
        if not isinstance(history, list) or not history:
            logger.debug(f"Task {task_id}: Empty or invalid history")
            return []

        # Clean messages - drop empty content
        messages = clean_messages(history)
        if not messages:
            logger.debug(f"Task {task_id}: No valid messages after cleaning")
            return []

        return messages
