"""Code Review Agent — Analyzes code for bugs, style issues, and suggests improvements."""

import os
import re
from pathlib import Path
from bindu.penguin.bindufy import bindufy

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def handler(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Process code review requests and return structured feedback."""
    user_message = messages[-1].get("content", "") if messages else ""

    # Simple code analysis logic
    issues = []
    suggestions = []
    score = 100

    # Check for common Python issues
    if "eval(" in user_message:
        issues.append({"severity": "high", "message": "🔴 Security risk: eval() can execute arbitrary code", "type": "security"})
        score -= 20

    if "except:" in user_message and "except Exception" not in user_message:
        issues.append({"severity": "high", "message": "🔴 Bare except clause catches all exceptions including SystemExit", "type": "error-handling"})
        score -= 15

    if "import *" in user_message:
        issues.append({"severity": "medium", "message": "🟡 Wildcard imports pollute namespace", "type": "style"})
        score -= 10

    if re.search(r"password\s*=\s*['\"]", user_message, re.IGNORECASE):
        issues.append({"severity": "high", "message": "🔴 Hardcoded password detected", "type": "security"})
        score -= 25

    if "print(" in user_message:
        issues.append({"severity": "low", "message": "🟢 Consider using logging instead of print()", "type": "best-practice"})
        score -= 5

    if "global " in user_message:
        issues.append({"severity": "medium", "message": "🟡 Global variables reduce code maintainability", "type": "design"})
        score -= 10

    # Check for missing docstrings
    if "def " in user_message and '"""' not in user_message and "'''" not in user_message:
        suggestions.append("📝 Add docstrings to your functions for better documentation")

    # Check for type hints
    if "def " in user_message and "->" not in user_message:
        suggestions.append("🏷️ Add return type hints for better code clarity")

    if not issues and not suggestions:
        suggestions.append("✅ Code looks clean! Consider adding unit tests for comprehensive coverage.")

    score = max(0, min(100, score))

    # Build response
    review = f"## 🔍 Code Review Report\n\n"
    review += f"**Quality Score: {score}/100** {'🟢' if score >= 80 else '🟡' if score >= 60 else '🔴'}\n\n"

    if issues:
        review += "### Issues Found\n"
        for issue in issues:
            review += f"- **[{issue['severity'].upper()}]** {issue['message']}\n"
        review += "\n"

    if suggestions:
        review += "### Suggestions\n"
        for s in suggestions:
            review += f"- {s}\n"
        review += "\n"

    review += f"\n*Reviewed by Code Review Agent v1.0 • {len(issues)} issues, {len(suggestions)} suggestions*"

    return [{"role": "assistant", "content": review}]


config = {
    "author": "naresh@example.com",
    "name": "code_review_agent",
    "description": "Analyzes code for bugs, security vulnerabilities, style issues, and suggests improvements.",
    "deployment": {"url": "http://localhost:3774", "expose": True},
    "skills": [str(PROJECT_ROOT / "skills" / "code-review")],
}

if __name__ == "__main__":
    bindufy(config, handler)
