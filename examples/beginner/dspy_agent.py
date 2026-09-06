"""
DSPy Agent Example — Bindu Integration
=======================================
WHAT EXISTED BEFORE:
    Only Agno, CrewAI, LangChain examples existed.
    No DSPy integration existed anywhere in the repo.

WHAT IS NEW:
    - First DSPy example in the Bindu ecosystem
    - Uses DSPy Signatures for structured, typed prompting
    - Supports multi-turn conversation history
    - Works with any OpenAI-compatible model
"""

import dspy
from bindu.penguin.bindufy import bindufy

# Configure DSPy with your preferred LLM
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)


# Define a DSPy Signature (typed prompt template)
class QASignature(dspy.Signature):
    """Answer the user's question clearly and concisely."""

    question: str = dspy.InputField(desc="The user's question")
    answer: str = dspy.OutputField(desc="A clear and concise answer")


# Build the DSPy program
qa_program = dspy.Predict(QASignature)


# Bindu handler — called when a message arrives
def handler(messages: list[dict]) -> list[dict]:
    """
    Process incoming messages using a DSPy QA program.

    Args:
        messages: Conversation history as list of role/content dicts

    Returns:
        List with a single assistant response message
    """
    last_message = " ".join(
        part.get("text", "")
        for part in messages[-1].get("parts", [])
        if part.get("kind") == "text"
    ).strip()
    result = qa_program(question=last_message)
    return [{"role": "assistant", "content": result.answer}]


# Bindu configuration
config = {
    "author": "varshayadav1722@gmail.com",
    "name": "dspy_agent",
    "description": "A DSPy-powered question answering agent",
    "deployment": {
        "url": "http://localhost:3773",
        "expose": True
    }
}


if __name__ == "__main__":
    print("Starting DSPy agent on http://localhost:3773 ...")
    bindufy(config, handler)
