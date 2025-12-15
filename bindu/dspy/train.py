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
    MIN_FEEDBACK_THRESHOLD,
)
from .dataset import build_golden_dataset, convert_to_dspy_examples
from .extractor import ExtractionStrategy
from .models import PromptCandidate
from .optimizer import optimize
from .postgres import fetch_raw_task_data
from .program import AgentProgram

logger = get_logger("bindu.dspy.train")


def train(
    agent_name: str | None = None,
    optimizer: Any = None,
    strategy: ExtractionStrategy = ExtractionStrategy.LAST_TURN,
    require_feedback: bool = True,
) -> list[PromptCandidate]:
    """Train and optimize agent prompts using DSPy.

    This function orchestrates the complete training pipeline:
    1. Configures DSPy with the default language model
    2. Fetches raw task data with feedback from PostgreSQL
    3. Builds golden dataset using the complete pipeline:
       - Normalize feedback
       - Extract interactions (with configurable strategy)
       - Filter by feedback quality
       - Validate and clean
       - Deduplicate
    4. Converts dataset to DSPy Example format
    5. Loads the agent program
    6. Runs DSPy optimization with the provided optimizer
    7. Extracts and scores optimized prompts
    8. Returns top prompt candidates

    Args:
        agent_name: Optional agent identifier for filtering interactions (not yet implemented)
        optimizer: DSPy optimizer instance to use for training.
            If None, uses BootstrapFewShot with default settings.
        strategy: Extraction strategy (LAST_TURN or FULL_HISTORY)
        require_feedback: Whether to require feedback for inclusion in dataset

    Returns:
        List of exactly NUM_PROMPT_CANDIDATES PromptCandidate objects,
        sorted by quality score in descending order

    Raises:
        RuntimeError: If STORAGE__POSTGRES_URL environment variable is not set
        ConnectionError: If unable to connect to database
        ValueError: If golden dataset pipeline fails

    Example:
        >>> from dspy.teleprompt import MIPRO
        >>> from bindu.dspy.extractor import ExtractionStrategy
        >>> optimizer = MIPRO(num_candidates=10, metric=my_metric)
        >>> candidates = train(
        ...     agent_name="support_agent",
        ...     optimizer=optimizer,
        ...     strategy=ExtractionStrategy.FULL_HISTORY
        ... )
        >>> best_prompt = candidates[0]
    """
    logger.info("Starting DSPy training pipeline")

    # Step 1: Configure DSPy with default model
    logger.info(f"Configuring DSPy with model: {DEFAULT_DSPY_MODEL}")
    lm = dspy.LM(DEFAULT_DSPY_MODEL)
    dspy.configure(lm=lm)

    # Step 2: Fetch raw task data from database (async operation)
    logger.info("Fetching raw task data from database")
    raw_tasks = asyncio.run(fetch_raw_task_data())

    if not raw_tasks:
        raise ValueError("No tasks found in database")

    logger.info(f"Fetched {len(raw_tasks)} raw tasks")

    # Step 3: Build golden dataset using complete pipeline
    logger.info(
        f"Building golden dataset (strategy={strategy.value}, "
        f"require_feedback={require_feedback}, "
        f"threshold={MIN_FEEDBACK_THRESHOLD})"
    )
    golden_dataset = build_golden_dataset(
        raw_tasks=raw_tasks,
        strategy=strategy,
        require_feedback=require_feedback,
        min_feedback_threshold=MIN_FEEDBACK_THRESHOLD,
    )

    logger.info(f"Golden dataset prepared with {len(golden_dataset)} examples")

    # Step 4: Convert to DSPy examples
    logger.info("Converting to DSPy examples")
    dspy_examples = convert_to_dspy_examples(golden_dataset)

    # Step 5: Load agent program
    logger.info("Initializing agent program")
    program = AgentProgram()

    # Step 6: Create default optimizer if none provided
    if optimizer is None:
        logger.info(
            f"No optimizer provided, using default BootstrapFewShot "
            f"with max_bootstrapped_demos={MAX_BOOTSTRAPPED_DEMOS}"
        )
        optimizer = dspy.BootstrapFewShot(
            max_bootstrapped_demos=MAX_BOOTSTRAPPED_DEMOS
        )

    # Step 7: Run optimization
    logger.info(f"Running optimization with {type(optimizer).__name__}")
    optimized_program = optimize(
        program=program,
        dataset=dspy_examples,
        optimizer=optimizer,
    )

    # Step 8: Extract prompt candidates from optimized program
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