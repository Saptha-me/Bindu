# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Dataset preparation for DSPy training.

This module handles filtering and conversion of raw interaction data into
golden datasets suitable for DSPy prompt optimization. It applies quality
thresholds and converts interactions into dspy.Example format.
"""

from __future__ import annotations

from typing import Any

import dspy

from bindu.utils.logging import get_logger

from .config import MIN_RATING_THRESHOLD, MIN_SCORE_THRESHOLD
from .models import Interaction

logger = get_logger("bindu.dspy.dataset")


def filter_high_quality_interactions(
    interactions: list[Interaction],
) -> list[Interaction]:
    """Filter interactions to only include high-quality training examples.

    Applies quality thresholds based on rating and score metadata to ensure
    the training dataset contains only the best examples.

    Args:
        interactions: Raw list of interactions from database

    Returns:
        Filtered list containing only high-quality interactions
    """
    filtered = []

    for interaction in interactions:
        metadata = interaction.metadata

        # Check rating threshold (if present)
        rating = metadata.get("rating")
        if rating is not None and rating < MIN_RATING_THRESHOLD:
            continue

        # Check score threshold (if present)
        score = metadata.get("score")
        if score is not None and score < MIN_SCORE_THRESHOLD:
            continue

        filtered.append(interaction)

    logger.info(
        f"Filtered {len(filtered)} high-quality interactions from {len(interactions)} total"
    )
    return filtered


def prepare_golden_dataset(
    interactions: list[Interaction],
) -> list[dict[str, Any]]:
    """Convert interactions into a golden dataset format.

    Transforms filtered interactions into a structured format suitable for
    DSPy training, with input-output pairs clearly separated.

    Args:
        interactions: High-quality filtered interactions

    Returns:
        List of dictionaries containing input-output pairs
    """
    dataset = []

    for interaction in interactions:
        # Extract input and output from interaction
        # Assume metadata contains input/output structure
        metadata = interaction.metadata
        input_text = metadata.get("input", interaction.text)
        output_text = metadata.get("output", interaction.text)

        dataset.append(
            {
                "id": str(interaction.id),
                "input": input_text,
                "output": output_text,
                "metadata": metadata,
            }
        )

    logger.info(f"Prepared golden dataset with {len(dataset)} examples")
    return dataset


def convert_to_dspy_examples(
    dataset: list[dict[str, Any]],
) -> list[dspy.Example]:
    """Convert golden dataset into DSPy Example format.

    Transforms the golden dataset into dspy.Example objects that can be
    used directly for prompt optimization.

    Args:
        dataset: Golden dataset with input-output pairs

    Returns:
        List of dspy.Example objects ready for training
    """
    examples = []

    for item in dataset:
        example = dspy.Example(
            input=item["input"],
            output=item["output"],
        ).with_inputs("input")

        examples.append(example)

    logger.info(f"Converted {len(examples)} examples to DSPy format")
    return examples