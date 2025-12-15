# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""Optimizer wrapper for DSPy prompt optimization.

This module provides a thin wrapper around DSPy optimizers, accepting any
optimizer implementation and delegating the compilation process to it.

The wrapper does not instantiate or configure optimizers - it receives them
as parameters, making the system flexible and decoupled from specific
optimization strategies.
"""

from __future__ import annotations

from typing import Any

import dspy

from bindu.utils.logging import get_logger

logger = get_logger("bindu.dspy.optimizer")


def optimize(
    program: dspy.Module,
    dataset: list[dspy.Example],
    optimizer: Any,
) -> dspy.Module:
    """Optimize a DSPy program using the provided optimizer.

    This function accepts any DSPy optimizer instance and uses it to compile
    the given program with the training dataset. The optimizer is responsible
    for the actual optimization logic and configuration.

    Args:
        program: The DSPy program to optimize (e.g., AgentProgram)
        dataset: List of DSPy examples for training
        optimizer: DSPy optimizer instance (e.g., BootstrapFewShot, MIPRO, etc.)

    Returns:
        Optimized DSPy program with refined prompts

    Example:
        >>> from dspy.teleprompt import BootstrapFewShot
        >>> optimizer = BootstrapFewShot(max_bootstrapped_demos=8)
        >>> optimized_program = optimize(program, dataset, optimizer)
    """
    logger.info(
        f"Starting optimization with {type(optimizer).__name__} "
        f"on {len(dataset)} examples"
    )

    # Delegate compilation to the optimizer
    # Most DSPy optimizers use compile(program, trainset=dataset)
    optimized_program = optimizer.compile(program, trainset=dataset)

    logger.info("Optimization completed successfully")
    return optimized_program
