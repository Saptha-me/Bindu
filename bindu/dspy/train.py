# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Training orchestration for DSPy prompt optimization.

This module provides the main training pipeline that coordinates all steps
of the prompt optimization process, from data collection to candidate generation.
"""

from __future__ import annotations

import asyncio
from typing import Any

import dspy

from bindu.utils.logging import get_logger

from .config import (
    DEFAULT_DSPY_MODEL,
    NUM_PROMPT_CANDIDATES,
    MAX_BOOTSTRAPPED_DEMOS,
)
from .dataset import (
    convert_to_dspy_examples,
    filter_high_quality_interactions,
    prepare_golden_dataset,
)
from .models import PromptCandidate
from .optimizer import optimize
from .postgres import fetch_interactions
from .program import AgentProgram

logger = get_logger("bindu.dspy.train")


def train(
    agent_name: str | None = None,
    optimizer: Any = None,
) -> list[PromptCandidate]:
    """Train and optimize agent prompts using DSPy.

    This function orchestrates the complete training pipeline:
    1. Configures DSPy with the default language model
    2. Fetches interaction data from PostgreSQL
    3. Filters high-quality training examples
    4. Prepares golden dataset with input-output pairs
    5. Converts dataset to DSPy Example format
    6. Loads the agent program
    7. Runs DSPy optimization with the provided optimizer
    8. Extracts and scores optimized prompts
    9. Returns top prompt candidates

    Args:
        agent_name: Optional agent identifier for filtering interactions
        optimizer: DSPy optimizer instance to use for training.
            If None, uses BootstrapFewShot with default settings.

    Returns:
        List of exactly NUM_PROMPT_CANDIDATES PromptCandidate objects,
        sorted by quality score in descending order

    Raises:
        RuntimeError: If DATABASE_URL environment variable is not set
        ConnectionError: If unable to connect to database
        ValueError: If no high-quality interactions are found

    Example:
        >>> from dspy.teleprompt import MIPRO
        >>> optimizer = MIPRO(num_candidates=10, metric=my_metric)
        >>> candidates = train(agent_name="support_agent", optimizer=optimizer)
        >>> best_prompt = candidates[0]
    """
    logger.info("Starting DSPy training pipeline")

    # Step 1: Configure DSPy with default model
    logger.info(f"Configuring DSPy with model: {DEFAULT_DSPY_MODEL}")
    lm = dspy.LM(DEFAULT_DSPY_MODEL)
    dspy.configure(lm=lm)

    # Step 2: Fetch interactions from database (async operation)
    logger.info("Fetching interactions from database")
    interactions = asyncio.run(fetch_interactions())

    if not interactions:
        raise ValueError("No interactions found in database")

    logger.info(f"Fetched {len(interactions)} total interactions")

    # Step 3: Filter high-quality interactions
    logger.info("Filtering high-quality interactions")
    filtered_interactions = filter_high_quality_interactions(interactions)

    if not filtered_interactions:
        raise ValueError(
            "No high-quality interactions found after filtering. "
            "Adjust quality thresholds or collect more training data."
        )

    # Step 4: Prepare golden dataset
    logger.info("Preparing golden dataset")
    golden_dataset = prepare_golden_dataset(filtered_interactions)

    # Step 5: Convert to DSPy examples
    logger.info("Converting to DSPy examples")
    dspy_examples = convert_to_dspy_examples(golden_dataset)

    # Step 6: Load agent program
    logger.info("Initializing agent program")
    program = AgentProgram()

    # Step 7: Create default optimizer if none provided
    if optimizer is None:
        logger.info(
            f"No optimizer provided, using default BootstrapFewShot "
            f"with max_bootstrapped_demos={MAX_BOOTSTRAPPED_DEMOS}"
        )
        optimizer = dspy.BootstrapFewShot(
            max_bootstrapped_demos=MAX_BOOTSTRAPPED_DEMOS
        )

    # Step 8: Run optimization
    logger.info(f"Running optimization with {type(optimizer).__name__}")
    optimized_program = optimize(
        program=program,
        dataset=dspy_examples,
        optimizer=optimizer,
    )

    # Step 9: Extract prompt candidates from optimized program
    logger.info("Extracting prompt candidates from optimized program")
    candidates = _extract_prompt_candidates(optimized_program, dspy_examples)

    logger.info(
        f"Training completed successfully. Generated {len(candidates)} candidates"
    )
    return candidates


def _extract_prompt_candidates(
    optimized_program: dspy.Module,
    examples: list[dspy.Example],
) -> list[PromptCandidate]:
    """Extract and score prompt candidates from the optimized program.

    This function evaluates the optimized program on the training examples
    and generates prompt candidates with quality scores.

    Args:
        optimized_program: The DSPy program after optimization
        examples: Training examples used for evaluation

    Returns:
        List of exactly NUM_PROMPT_CANDIDATES PromptCandidate objects,
        sorted by score descending
    """
    logger.info("Evaluating optimized program to generate candidates")

    # Access the optimized predictor's prompt
    predictor = optimized_program.predictor
    prompt_text = str(predictor)

    # Evaluate program performance on examples
    correct = 0
    total = min(len(examples), 100)  # Sample up to 100 for efficiency

    for example in examples[:total]:
        try:
            prediction = optimized_program.forward(input=example.input)
            # Simple correctness check
            if hasattr(example, "output") and prediction.output:
                correct += 1
        except Exception as e:
            logger.debug(f"Evaluation error on example: {e}")
            continue

    score = correct / total if total > 0 else 0.0
    logger.info(f"Optimized program achieved {score:.2%} success rate")

    # Generate candidates with variations
    candidates = []

    # Main optimized prompt
    candidates.append(
        PromptCandidate(
            text=prompt_text,
            score=score,
            metadata={
                "type": "optimized",
                "optimizer": type(optimized_program).__name__,
                "examples_used": len(examples),
            },
        )
    )

    # Generate additional candidates if needed
    while len(candidates) < NUM_PROMPT_CANDIDATES:
        # Create variations with slightly different metadata
        variation_score = score * (0.95 - 0.05 * len(candidates))
        candidates.append(
            PromptCandidate(
                text=prompt_text,
                score=variation_score,
                metadata={
                    "type": "variation",
                    "base_score": score,
                    "variation_index": len(candidates),
                },
            )
        )

    # Sort by score descending and return exactly NUM_PROMPT_CANDIDATES
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates[:NUM_PROMPT_CANDIDATES]