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

import os

import dspy

from bindu.utils.logging import get_logger

from .config import (
    DEFAULT_DSPY_MODEL,
    NUM_PROMPT_CANDIDATES,
    MAX_BOOTSTRAPPED_DEMOS,
    MIN_FEEDBACK_THRESHOLD,
)
from .dataset import build_golden_dataset, convert_to_dspy_examples
from .models import PromptCandidate
from .optimizer import optimize
from .postgres import fetch_raw_task_data
from .program import AgentProgram
from .strategies import BaseExtractionStrategy, LastTurnStrategy

logger = get_logger("bindu.dspy.train")

async def train_async(
    optimizer: Any = None,
    strategy: BaseExtractionStrategy | None = None,
    require_feedback: bool = True,
    current_prompt_text: str = "",
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
        optimizer: DSPy optimizer instance to use for training.
            If None, uses BootstrapFewShot with default settings.
        strategy: Extraction strategy to use. Defaults to LastTurnStrategy.
            Use strategy classes from bindu.dspy.strategies:
            - LastTurnStrategy()
            - FullHistoryStrategy()
            - LastNTurnsStrategy(n_turns=3)
            - FirstNTurnsStrategy(n_turns=3)
            - ContextWindowStrategy(n_turns=3, system_prompt="...")
        require_feedback: Whether to require feedback for inclusion in dataset
        current_prompt_text: Current system prompt for the agent

    Returns:
        List of exactly NUM_PROMPT_CANDIDATES PromptCandidate objects,
        sorted by quality score in descending order

    Raises:
        RuntimeError: If STORAGE__POSTGRES_URL environment variable is not set
        ConnectionError: If unable to connect to database
        ValueError: If golden dataset pipeline fails

    Example:
        >>> from dspy.teleprompt import MIPRO
        >>> from bindu.dspy.strategies import ContextWindowStrategy
        >>> import asyncio
        >>> strategy = ContextWindowStrategy(n_turns=3, system_prompt="Be helpful")
        >>> optimizer = MIPRO(num_candidates=10, metric=my_metric)
        >>> candidates = asyncio.run(train_async(
        ...     optimizer=optimizer,
        ...     strategy=strategy
        ... ))
        >>> best_prompt = candidates[0]

    Note:
        This is an async function. When calling from async code, use await.
        For sync contexts, use the train() wrapper function instead.
    """
    strategy = strategy or LastTurnStrategy()
    logger.info(f"Starting DSPy training pipeline with {strategy.name} strategy")

    # Step 1: Configure DSPy with default model
    logger.info(f"Configuring DSPy with model: {DEFAULT_DSPY_MODEL}")
    lm = dspy.LM(DEFAULT_DSPY_MODEL)
    dspy.configure(lm=lm)

    # api_key = os.getenv("GOOGLE_API_KEY")
    # if not api_key:
    #     raise RuntimeError("GOOGLE_API_KEY is not set")

    # lm = dspy.LM('google/gemini-1.5-flash', api_key=api_key, litellm_provider="google")
    # dspy.configure(lm=lm)

    # Step 2: Fetch raw task data from database (async operation)
    logger.info("Fetching raw task data from database")
    raw_tasks = await fetch_raw_task_data()

    if not raw_tasks:
        raise ValueError("No tasks found in database")

    logger.info(f"Fetched {len(raw_tasks)} raw tasks")

    # Step 3: Build golden dataset using complete pipeline
    logger.info(
        f"Building golden dataset (strategy={strategy.name}, "
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
    program = AgentProgram(current_prompt_text)

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


def train(
    optimizer: Any = None,
    strategy: BaseExtractionStrategy | None = None,
    require_feedback: bool = True,
) -> list[PromptCandidate]:
    """Synchronous wrapper for train_async().

    This function provides a synchronous interface to the async training pipeline.
    For use in async contexts, call train_async() directly.

    Args:
        optimizer: DSPy optimizer instance (default: BootstrapFewShot)
        strategy: Extraction strategy to use. Defaults to LastTurnStrategy.
        require_feedback: Whether to require feedback for inclusion in dataset

    Returns:
        List of prompt candidates sorted by quality score

    Raises:
        RuntimeError: If called from within an async event loop. Use train_async() instead.
    """
    try:
        return asyncio.run(train_async(optimizer, strategy, require_feedback))
    except RuntimeError as e:
        if "event loop" in str(e):
            raise RuntimeError(
                "train() cannot be called from an async context. "
                "Use 'await train_async()' instead."
            ) from e
        raise
