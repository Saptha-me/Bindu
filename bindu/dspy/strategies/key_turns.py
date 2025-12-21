# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We love you! - Bindu

"""Key turns extraction strategy.

This strategy selects the most semantically relevant turns from a conversation
based on text similarity to the final turn.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from bindu.utils.logging import get_logger

from ..models import Interaction
from .base import BaseExtractionStrategy, parse_turns
from .similarity import SimilarityMethod, compute_similarity

logger = get_logger("bindu.dspy.strategies.key_turns")


class KeyTurnsStrategy(BaseExtractionStrategy):
    """Extract key turns from conversation based on semantic similarity to final turn.

    This strategy identifies the most relevant turns in a conversation by
    calculating text similarity between each turn and the final user query.
    This helps focus on contextually important information while discarding
    less relevant turns.

    The algorithm:
    1. Parse conversation into turns
    2. Calculate similarity between each earlier turn and the final turn
    3. Rank turns by similarity score
    4. Select top N most similar turns
    5. Preserve chronological order in output

    Example with a 6-turn conversation about Python:
        Turn 1: User asks about loops (low similarity to final)
        Turn 2: User asks about functions (medium similarity)
        Turn 3: User asks about classes (high similarity)
        Turn 4: User asks about databases (low similarity)
        Turn 5: User asks about ORM classes (high similarity)
        Turn 6: User asks about SQLAlchemy models (final turn)

        With n_turns=3 and using the final turn for similarity:
        - Selects turns 3, 5, 6 (most similar to "SQLAlchemy models")
        - Output preserves chronological order: 3 -> 5 -> 6

    Usage:
        strategy = KeyTurnsStrategy(n_turns=3, similarity_method="jaccard")
        strategy = KeyTurnsStrategy(n_turns=4, similarity_method="weighted")
        strategy = KeyTurnsStrategy(n_turns=3, similarity_method="overlap")

    Args:
        n_turns: Number of key turns to extract (default: 3, minimum: 1)
        similarity_method: Method for calculating text similarity (default: "jaccard")
            - "jaccard": Jaccard coefficient (intersection/union of word sets)
            - "weighted": TF-IDF style weighting for rare terms
            - "overlap": Overlap coefficient (intersection/min set size)
        include_final: Whether to always include the final turn (default: True)
        use_both_messages: Whether to include assistant response in similarity calc (default: True)
    """

    def __init__(
        self,
        n_turns: int = 3,
        similarity_method: SimilarityMethod = "jaccard",
        include_final: bool = True,
        use_both_messages: bool = True,
    ):
        self.n_turns = max(1, n_turns)
        self.similarity_method = similarity_method
        self.include_final = include_final
        self.use_both_messages = use_both_messages

    @property
    def name(self) -> str:
        return "key_turns"

    def extract(
        self,
        task_id: UUID,
        messages: list[dict[str, Any]],
        feedback_score: float | None = None,
        feedback_type: str | None = None,
    ) -> Interaction | None:
        """Extract key turns based on semantic similarity to final turn.

        Algorithm:
        1. Parse messages into turns
        2. Get final turn as reference
        3. Calculate similarity scores for earlier turns
        4. Select top N most similar turns
        5. Format as user_input with last agent response as output
        """
        turns = parse_turns(messages)

        if not turns:
            logger.debug(f"Task {task_id}: No complete turns found in history")
            return None

        # If we have fewer turns than requested, use all turns
        if len(turns) <= self.n_turns:
            return self._create_interaction_from_turns(
                task_id, turns, feedback_score, feedback_type
            )

        # Get the final turn as reference for similarity calculation
        final_turn = turns[-1]
        reference_text = self._get_turn_text(final_turn)

        # Build corpus for weighted similarity (if using that method)
        corpus = [self._get_turn_text(turn) for turn in turns]

        # Calculate similarity scores for all turns except the final one
        scored_turns: list[tuple[int, float, tuple[str, str]]] = []
        for idx, turn in enumerate(turns[:-1]):
            turn_text = self._get_turn_text(turn)
            score = compute_similarity(
                turn_text,
                reference_text,
                method=self.similarity_method,
                corpus=corpus if self.similarity_method == "weighted" else None,
            )
            scored_turns.append((idx, score, turn))

        # Sort by similarity score (descending)
        scored_turns.sort(key=lambda x: x[1], reverse=True)

        # Select top turns (leaving room for final turn if include_final)
        num_to_select = self.n_turns - 1 if self.include_final else self.n_turns
        selected = scored_turns[:num_to_select]

        # Sort selected turns back to chronological order
        selected.sort(key=lambda x: x[0])

        # Build final turn list
        key_turns = [turn for _, _, turn in selected]

        # Always include the final turn
        if self.include_final:
            key_turns.append(final_turn)

        if not key_turns:
            logger.debug(f"Task {task_id}: No key turns selected")
            return None

        return self._create_interaction_from_turns(
            task_id, key_turns, feedback_score, feedback_type
        )

    def _get_turn_text(self, turn: tuple[str, str]) -> str:
        """Get text representation of a turn for similarity calculation.

        Args:
            turn: (user_content, assistant_content) tuple

        Returns:
            Text to use for similarity calculation
        """
        user_msg, assistant_msg = turn
        if self.use_both_messages:
            return f"{user_msg} {assistant_msg}"
        return user_msg

    def _create_interaction_from_turns(
        self,
        task_id: UUID,
        turns: list[tuple[str, str]],
        feedback_score: float | None,
        feedback_type: str | None,
    ) -> Interaction | None:
        """Create an Interaction from selected key turns.

        Args:
            task_id: The task ID
            turns: List of selected (user_content, assistant_content) tuples
            feedback_score: Normalized feedback score
            feedback_type: Type of feedback

        Returns:
            Interaction object or None if creation fails
        """
        if not turns:
            return None

        # Get the last agent response as output
        agent_output = turns[-1][1]

        if len(turns) == 1:
            user_input = turns[0][0]
        else:
            # Format with context labels
            lines = []
            for i, (user_msg, assistant_msg) in enumerate(turns[:-1]):
                lines.append(f"[Key context {i + 1}]")
                lines.append(f"User: {user_msg}")
                lines.append(f"Assistant: {assistant_msg}")

            lines.append("")
            lines.append("[Current query]")
            lines.append(f"User: {turns[-1][0]}")

            user_input = "\n".join(lines)

        if not user_input or not agent_output:
            return None

        return Interaction(
            id=task_id,
            user_input=user_input,
            agent_output=agent_output,
            feedback_score=feedback_score,
            feedback_type=feedback_type,
        )
