# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/getbindu/Bindu/issues/new/choose    |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🌻

"""DSPy signature definition for agent response generation.

This module defines the input-output signature used by DSPy to understand
the structure of the agent's task. The signature specifies what the program
receives as input and what it should produce as output.
"""

from __future__ import annotations

import dspy


class AgentSignature(dspy.Signature):
    """Signature for agent response generation.

    This signature defines a simple input-output mapping where the agent
    receives a user query or context and produces a response. It serves
    as the contract between the DSPy optimizer and the agent program.

    The signature uses DSPy's standard field definitions to specify:
    - input: The user's query or request
    - output: The agent's generated response
    """

    input = dspy.InputField(desc="User query or request")
    output = dspy.OutputField(desc="Agent response")
