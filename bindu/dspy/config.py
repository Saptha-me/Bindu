# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Configuration constants for DSPy integration.

This module defines the constants used for DSPy prompt optimization,
including model settings, filtering thresholds, and optimization parameters.
"""

from __future__ import annotations

# DSPy Model Configuration
DEFAULT_DSPY_MODEL = "gpt-3.5-turbo"
"""Default language model for DSPy optimization."""

# Dataset Filtering Thresholds
MIN_FEEDBACK_THRESHOLD = 0.8
"""Minimum normalized feedback score [0.0, 1.0] for interactions to be included in training dataset."""

# Golden Dataset Constraints
MIN_EXAMPLES = 10
"""Minimum number of examples required in golden dataset."""

MAX_EXAMPLES = 10000
"""Maximum number of examples allowed in golden dataset."""

MIN_INPUT_LENGTH = 10
"""Minimum character length for user input."""

MIN_OUTPUT_LENGTH = 10
"""Minimum character length for agent output."""

MAX_FULL_HISTORY_LENGTH = 10000
"""Maximum character length for full history extraction strategy."""

# Prompt Optimization Parameters
NUM_PROMPT_CANDIDATES = 3
"""Number of optimized prompt candidates to generate and return."""

MAX_BOOTSTRAPPED_DEMOS = 8
"""Maximum number of bootstrapped demonstrations for few-shot learning."""

# Database Query Limits
MAX_INTERACTIONS_QUERY_LIMIT = 10000
"""Maximum number of interactions to fetch from database in a single query."""
