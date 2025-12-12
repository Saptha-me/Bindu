"""Calculator Agent - Does basic math without needing any API keys.

Each calculation is independent - doesn't need conversation history.
Useful for testing Bindu or as a template for simple agents.
"""

from bindu.penguin.bindufy import bindufy
import re


def parse_math_expression(text):
    """Pull out the math part from natural language.

    Handles stuff like "what is 2+2" or "calculate 100/5".
    """
    # Strip out common phrases
    text = text.lower()
    for phrase in ["what is", "what's", "calculate", "compute", "solve"]:
        text = text.replace(phrase, "")

    # Clean up whitespace and trailing punctuation
    text = text.strip().rstrip("? ! .").strip()

    return text


def safe_calculate(expression):
    """Run the math safely, only allows basic operations."""
    safe_expr = re.sub(r"[^0-9+\-*/().\s]", "", expression)

    if not safe_expr.strip():
        return "Hmm, I couldn't find a math expression in that."

    try:
        result = eval(safe_expr, {"__builtins__": {}}, {})
        return f"The answer is: {result}"
    except ZeroDivisionError:
        return "Can't divide by zero!"
    except (SyntaxError, NameError):
        return "That doesn't look like valid math to me."
    except Exception as e:
        return f"Something went wrong:  {str(e)}"


def handler(messages):
    """Process incoming messages and do the math."""
    last_message = messages[-1]["content"]

    # Extract and calculate
    expression = parse_math_expression(last_message)
    result = safe_calculate(expression)

    return [{"role": "assistant", "content": result}]


config = {
    "author": "your.email@example.com",
    "name": "calculator_agent",
    "description": "Simple calculator for basic math operations",
    "deployment": {"url": "http://localhost:3773", "expose": True},
    "skills": ["skills/calculation"],
}

if __name__ == "__main__":
    bindufy(config, handler)
