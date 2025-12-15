# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Dataset preparation for DSPy training.

This module implements the complete golden dataset pipeline:
1. Normalize feedback from raw task data
2. Extract interactions using configurable strategies
3. Filter by feedback quality
4. Validate and clean interactions
5. Deduplicate examples
6. Prepare final golden dataset

The pipeline transforms raw PostgreSQL task data into high-quality
training examples for DSPy prompt optimization.
"""

from __future__ import annotations

from typing import Any

import dspy

from bindu.utils.logging import get_logger

from .config import (
    MAX_EXAMPLES,
    MIN_EXAMPLES,
    MIN_FEEDBACK_THRESHOLD,
    MIN_INPUT_LENGTH,
    MIN_OUTPUT_LENGTH,
)
from .extractor import ExtractionStrategy, InteractionExtractor
from .models import Interaction
from .postgres import RawTaskData

logger = get_logger("bindu.dspy.dataset")


def normalize_feedback(feedback_data: dict[str, Any] | None) -> tuple[float | None, str | None]:
    """Normalize feedback data to a single numeric score [0.0, 1.0].

    Accepts multiple feedback formats:
    - { rating: 1-5 } → normalized to 0.0-1.0
    - { thumbs_up: true/false } → 1.0 or 0.0
    - Missing/invalid → None

    Args:
        feedback_data: Raw feedback data from database

    Returns:
        Tuple of (normalized_score, feedback_type) or (None, None)
    """
    if not feedback_data:
        return None, None

    # Try rating format (1-5 scale)
    rating = feedback_data.get("rating")
    if rating is not None:
        try:
            rating_val = float(rating)
            if 1 <= rating_val <= 5:
                normalized = rating_val / 5.0
                return normalized, "rating"
        except (ValueError, TypeError):
            pass

    # Try thumbs_up format
    thumbs_up = feedback_data.get("thumbs_up")
    if thumbs_up is not None:
        if isinstance(thumbs_up, bool):
            return 1.0 if thumbs_up else 0.0, "thumbs_up"
        # Handle string "true"/"false"
        if isinstance(thumbs_up, str):
            thumbs_up_lower = thumbs_up.lower()
            if thumbs_up_lower in ("true", "1", "yes"):
                return 1.0, "thumbs_up"
            elif thumbs_up_lower in ("false", "0", "no"):
                return 0.0, "thumbs_up"

    return None, None


def extract_interactions(
    raw_tasks: list[RawTaskData],
    strategy: ExtractionStrategy = ExtractionStrategy.LAST_TURN,
) -> list[Interaction]:
    """Extract interactions from raw task data.

    For each task:
    1. Normalize feedback
    2. Extract interaction using specified strategy
    3. Collect all valid interactions

    Args:
        raw_tasks: Raw task data from database
        strategy: Extraction strategy to use

    Returns:
        List of extracted interactions
    """
    extractor = InteractionExtractor(strategy=strategy)
    interactions: list[Interaction] = []

    for task in raw_tasks:
        # Normalize feedback
        feedback_score, feedback_type = normalize_feedback(task.feedback_data)

        # Extract interaction
        interaction = extractor.extract(
            task_id=task.id,
            history=task.history,
            feedback_score=feedback_score,
            feedback_type=feedback_type,
        )

        if interaction:
            interactions.append(interaction)

    logger.info(
        f"Extracted {len(interactions)} interactions from {len(raw_tasks)} tasks "
        f"using {strategy.value} strategy"
    )
    return interactions


def filter_by_feedback_quality(
    interactions: list[Interaction],
    require_feedback: bool = True,
    min_threshold: float = MIN_FEEDBACK_THRESHOLD,
) -> list[Interaction]:
    """Filter interactions by feedback quality.

    Rules:
    - If feedback exists: must be >= min_threshold
    - If no feedback: drop (if require_feedback=True) or keep (if False)

    Args:
        interactions: List of interactions to filter
        require_feedback: Whether to drop interactions without feedback
        min_threshold: Minimum feedback score threshold

    Returns:
        Filtered list of high-quality interactions
    """
    filtered: list[Interaction] = []

    for interaction in interactions:
        # Check if feedback exists
        if interaction.feedback_score is None:
            if not require_feedback:
                filtered.append(interaction)
            continue

        # Check threshold
        if interaction.feedback_score >= min_threshold:
            filtered.append(interaction)

    logger.info(
        f"Filtered {len(filtered)} high-quality interactions from {len(interactions)} total "
        f"(require_feedback={require_feedback}, threshold={min_threshold})"
    )
    return filtered


def validate_and_clean_interactions(
    interactions: list[Interaction],
) -> list[Interaction]:
    """Validate and clean interactions.

    Validation rules:
    - Minimum length for input and output
    - Output must not be identical to input
    - Remove excessive whitespace
    - Normalize Unicode

    Args:
        interactions: List of interactions to validate

    Returns:
        List of valid, cleaned interactions
    """
    validated: list[Interaction] = []

    for interaction in interactions:
        # Clean whitespace
        user_input = " ".join(interaction.user_input.split())
        agent_output = " ".join(interaction.agent_output.split())

        # Check minimum lengths
        if len(user_input) < MIN_INPUT_LENGTH:
            continue
        if len(agent_output) < MIN_OUTPUT_LENGTH:
            continue

        # Check not identical
        if user_input == agent_output:
            continue

        # Create cleaned interaction
        validated.append(
            Interaction(
                id=interaction.id,
                user_input=user_input,
                agent_output=agent_output,
                feedback_score=interaction.feedback_score,
                feedback_type=interaction.feedback_type,
            )
        )

    logger.info(
        f"Validated {len(validated)} interactions from {len(interactions)} total "
        f"(min_input={MIN_INPUT_LENGTH}, min_output={MIN_OUTPUT_LENGTH})"
    )
    return validated


def deduplicate_interactions(interactions: list[Interaction]) -> list[Interaction]:
    """Remove duplicate interactions based on (user_input, agent_output).

    Args:
        interactions: List of interactions to deduplicate

    Returns:
        List of unique interactions
    """
    seen: set[tuple[str, str]] = set()
    unique: list[Interaction] = []

    for interaction in interactions:
        key = (interaction.user_input, interaction.agent_output)
        if key not in seen:
            seen.add(key)
            unique.append(interaction)

    if len(unique) < len(interactions):
        logger.info(f"Removed {len(interactions) - len(unique)} duplicate interactions")

    return unique


def prepare_golden_dataset(
    interactions: list[Interaction],
) -> list[dict[str, Any]]:
    """Prepare golden dataset in DSPy-ready format.

    Converts cleaned interactions into simple input-output pairs.

    Args:
        interactions: Validated, deduplicated interactions

    Returns:
        Golden dataset ready for DSPy training
    """
    dataset: list[dict[str, Any]] = []

    for interaction in interactions:
        dataset.append(
            {
                "input": interaction.user_input,
                "output": interaction.agent_output,
            }
        )

    logger.info(f"Prepared golden dataset with {len(dataset)} examples")
    return dataset


def validate_dataset_size(dataset: list[dict[str, Any]]) -> None:
    """Validate that dataset size is within acceptable bounds.

    Args:
        dataset: Golden dataset to validate

    Raises:
        ValueError: If dataset is too small or too large
    """
    size = len(dataset)

    if size < MIN_EXAMPLES:
        raise ValueError(
            f"Dataset too small: {size} examples (minimum required: {MIN_EXAMPLES})"
        )

    if size > MAX_EXAMPLES:
        logger.warning(
            f"Dataset size ({size}) exceeds maximum ({MAX_EXAMPLES}). "
            f"Consider sampling or adjusting query limit."
        )

    logger.info(f"Dataset size validation passed: {size} examples")


def build_golden_dataset(
    raw_tasks: list[RawTaskData],
    strategy: ExtractionStrategy = ExtractionStrategy.LAST_TURN,
    require_feedback: bool = True,
    min_feedback_threshold: float = MIN_FEEDBACK_THRESHOLD,
) -> list[dict[str, Any]]:
    """Build complete golden dataset from raw task data.

    This is the main pipeline function that orchestrates all steps:
    1. Extract interactions from raw tasks
    2. Filter by feedback quality
    3. Validate and clean
    4. Deduplicate
    5. Prepare golden dataset
    6. Validate size

    Args:
        raw_tasks: Raw task data from database
        strategy: Extraction strategy to use
        require_feedback: Whether to require feedback for inclusion
        min_feedback_threshold: Minimum feedback score threshold

    Returns:
        Golden dataset ready for DSPy training

    Raises:
        ValueError: If dataset is too small or pipeline fails
    """
    logger.info("Starting golden dataset pipeline")

    # Step 1: Extract interactions
    interactions = extract_interactions(raw_tasks, strategy=strategy)
    if not interactions:
        raise ValueError("No interactions extracted from raw tasks")

    # Step 2: Filter by feedback quality
    interactions = filter_by_feedback_quality(
        interactions,
        require_feedback=require_feedback,
        min_threshold=min_feedback_threshold,
    )
    if not interactions:
        raise ValueError("No interactions passed feedback quality filter")

    # Step 3: Validate and clean
    interactions = validate_and_clean_interactions(interactions)
    if not interactions:
        raise ValueError("No interactions passed validation")

    # Step 4: Deduplicate
    interactions = deduplicate_interactions(interactions)
    if not interactions:
        raise ValueError("No interactions after deduplication")

    # Step 5: Prepare golden dataset
    dataset = prepare_golden_dataset(interactions)

    # Step 6: Validate size
    validate_dataset_size(dataset)

    logger.info("Golden dataset pipeline completed successfully")
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
    examples: list[dspy.Example] = []

    for item in dataset:
        example = dspy.Example(
            input=item["input"],
            output=item["output"],
        ).with_inputs("input")

        examples.append(example)

    logger.info(f"Converted {len(examples)} examples to DSPy format")
    return examples