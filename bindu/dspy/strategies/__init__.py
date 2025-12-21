# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We love you! - Bindu

"""Extraction strategies for DSPy training data.

This module provides different strategies for extracting user-agent interactions
from task history. Each strategy is a self-contained class with its own
configuration parameters.

Available Strategies:
    - LastTurnStrategy: Extract only the last user-assistant turn
    - FullHistoryStrategy: Extract first user input and entire conversation
    - LastNTurnsStrategy: Extract the last N turns with context
    - FirstNTurnsStrategy: Extract the first N turns
    - ContextWindowStrategy: Extract last N turns with concatenated user messages
    - SlidingWindowStrategy: Generate multiple examples using sliding windows
    - SummaryContextStrategy: Summarize earlier context for long conversations
    - KeyTurnsStrategy: Select semantically relevant turns using text similarity

Usage:
    # Simple strategies - no config needed
    strategy = LastTurnStrategy()

    # Strategies with config - params in constructor
    strategy = ContextWindowStrategy(n_turns=3, system_prompt="You are helpful.")
    strategy = KeyTurnsStrategy(n_turns=3, similarity_method="weighted")

    # Factory approach
    strategy = get_strategy("context_window", n_turns=3, system_prompt="You are helpful.")
    strategy = get_strategy("key_turns", n_turns=4, similarity_method="jaccard")
"""

from __future__ import annotations

from typing import Any

from .base import BaseExtractionStrategy, parse_turns
from .context_window import ContextWindowStrategy
from .first_n_turns import FirstNTurnsStrategy
from .full_history import FullHistoryStrategy
from .key_turns import KeyTurnsStrategy
from .last_n_turns import LastNTurnsStrategy
from .last_turn import LastTurnStrategy
from .similarity import (
    SIMILARITY_METHODS,
    SimilarityMethod,
    compute_similarity,
    jaccard_similarity,
    overlap_similarity,
    weighted_similarity,
)
from .sliding_window import SlidingWindowStrategy
from .summary_context import SummaryContextStrategy

# Strategy registry for factory pattern
STRATEGIES: dict[str, type[BaseExtractionStrategy]] = {
    "last_turn": LastTurnStrategy,
    "full_history": FullHistoryStrategy,
    "last_n_turns": LastNTurnsStrategy,
    "first_n_turns": FirstNTurnsStrategy,
    "context_window": ContextWindowStrategy,
    "sliding_window": SlidingWindowStrategy,
    "summary_context": SummaryContextStrategy,
    "key_turns": KeyTurnsStrategy,
}


def get_strategy(name: str, **kwargs: Any) -> BaseExtractionStrategy:
    """Factory function to create a strategy by name.

    Args:
        name: Strategy name (e.g., "last_turn", "context_window", "key_turns")
        **kwargs: Strategy-specific configuration parameters

    Returns:
        Configured strategy instance

    Raises:
        ValueError: If strategy name is not recognized

    Examples:
        >>> strategy = get_strategy("last_turn")
        >>> strategy = get_strategy("context_window", n_turns=5, system_prompt="Be helpful")
        >>> strategy = get_strategy("key_turns", n_turns=3, similarity_method="weighted")
    """
    if name not in STRATEGIES:
        available = ", ".join(STRATEGIES.keys())
        raise ValueError(f"Unknown strategy: {name}. Available: {available}")

    strategy_class = STRATEGIES[name]
    return strategy_class(**kwargs)


__all__ = [
    # Base classes and utilities
    "BaseExtractionStrategy",
    "parse_turns",
    # Strategies
    "LastTurnStrategy",
    "FullHistoryStrategy",
    "LastNTurnsStrategy",
    "FirstNTurnsStrategy",
    "ContextWindowStrategy",
    "SlidingWindowStrategy",
    "SummaryContextStrategy",
    "KeyTurnsStrategy",
    # Factory
    "STRATEGIES",
    "get_strategy",
    # Similarity functions
    "SimilarityMethod",
    "SIMILARITY_METHODS",
    "compute_similarity",
    "jaccard_similarity",
    "overlap_similarity",
    "weighted_similarity",
]
