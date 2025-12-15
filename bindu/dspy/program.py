# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""DSPy program module for agent response generation.

This module defines the agent program whose prompt will be optimized using
DSPy's teleprompter system. The program represents the core logic that
processes inputs and generates responses.
"""

from __future__ import annotations

import dspy

from .signature import AgentSignature


class AgentProgram(dspy.Module):
    """Agent program for response generation.

    This program implements the core agent logic using DSPy's Module system.
    It takes user input and generates a response using the defined signature.

    The program uses DSPy's Predict module to generate predictions based on
    the AgentSignature. During optimization, DSPy will refine the prompts
    used by this predictor to improve output quality.

    The program is intentionally minimal - it contains only the prediction
    logic without training, evaluation, or instrumentation concerns.
    """

    def __init__(self) -> None:
        """Initialize the agent program with a predictor."""
        super().__init__()
        self.predictor = dspy.Predict(AgentSignature)

    def forward(self, input: str) -> dspy.Prediction:
        """Generate a response for the given input.

        This method is called during both training and inference. It takes
        the user input and returns a prediction containing the agent's response.

        Args:
            input: User query or request

        Returns:
            DSPy prediction containing the agent's response
        """
        return self.predictor(input=input)
