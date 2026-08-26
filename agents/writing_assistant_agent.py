"""Writing Assistant Agent — Helps with grammar, summarization, and content generation."""

import re
from pathlib import Path
from bindu.penguin.bindufy import bindufy

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# Common grammar mistakes database
GRAMMAR_FIXES = {
    r"\btheir\s+(going|coming|doing|trying|making)": ("They're", "their → they're (contraction of 'they are')"),
    r"\byour\s+(welcome|right|wrong|the best)": ("You're", "your → you're (contraction of 'you are')"),
    r"\bits\s+(a|the|going|been|not)": ("It's", "its → it's (contraction of 'it is')"),
    r"\bthen\b(?=\s+(?:I|you|we|he|she|they)\s+(?:would|could|should))": ("than", "then → than (comparison)"),
    r"\beffect\b(?=\s+(?:the|a|my|your|our))": ("affect", "effect → affect (verb form)"),
    r"\balot\b": ("a lot", "alot → a lot (two words)"),
    r"\btommorow\b": ("tomorrow", "tommorow → tomorrow (spelling)"),
    r"\brecieve\b": ("receive", "recieve → receive (i before e)"),
    r"\boccured\b": ("occurred", "occured → occurred (double r)"),
    r"\bseperate\b": ("separate", "seperate → separate (spelling)"),
}


def handler(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Process writing assistance requests."""
    user_message = messages[-1].get("content", "") if messages else ""
    lower = user_message.lower()

    result = "## ✍️ Writing Assistant Report\n\n"

    # Detect the action
    if any(kw in lower for kw in ["summarize", "summary", "tldr", "shorten"]):
        result += _summarize(user_message)
    elif any(kw in lower for kw in ["check", "grammar", "proofread", "correct", "fix"]):
        result += _grammar_check(user_message)
    elif any(kw in lower for kw in ["write", "generate", "compose", "draft", "create"]):
        result += _generate_content(user_message)
    elif any(kw in lower for kw in ["rewrite", "improve", "polish", "rephrase"]):
        result += _rewrite(user_message)
    else:
        # Default: do a grammar check
        result += _grammar_check(user_message)

    result += f"\n*Processed by Writing Assistant Agent v1.0*"
    return [{"role": "assistant", "content": result}]


def _grammar_check(text: str) -> str:
    """Check text for grammar issues."""
    corrections = []
    for pattern, (fix, reason) in GRAMMAR_FIXES.items():
        if re.search(pattern, text, re.IGNORECASE):
            corrections.append({"reason": reason, "suggestion": fix})

    # Count sentences and words
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    words = text.split()
    avg_sentence_len = len(words) / max(len(sentences), 1)

    output = "### Grammar Check Results\n\n"

    if corrections:
        output += f"Found **{len(corrections)} issue(s)**:\n\n"
        for c in corrections:
            output += f"- 🔧 **{c['reason']}** → Use: *{c['suggestion']}*\n"
    else:
        output += "✅ No grammar issues found!\n"

    output += f"\n### Readability Metrics\n"
    output += f"| Metric | Value |\n|---|---|\n"
    output += f"| **Words** | {len(words)} |\n"
    output += f"| **Sentences** | {len(sentences)} |\n"
    output += f"| **Avg words/sentence** | {avg_sentence_len:.1f} |\n"

    if avg_sentence_len > 25:
        output += f"\n⚠️ Sentences are long (avg {avg_sentence_len:.0f} words). Consider breaking them up.\n"
    elif avg_sentence_len < 8:
        output += f"\n💡 Sentences are short. Consider combining some for better flow.\n"
    else:
        output += f"\n✅ Good sentence length for readability.\n"

    return output


def _summarize(text: str) -> str:
    """Summarize the provided text."""
    # Remove the instruction keywords
    clean = re.sub(r'(?i)(summarize|summary|tldr|shorten|please|can you|this|:)', '', text).strip()
    sentences = [s.strip() for s in re.split(r'[.!?]+', clean) if len(s.strip()) > 10]

    output = "### Summary\n\n"
    if sentences:
        # Take key sentences (first, middle, last)
        key = []
        if len(sentences) >= 1:
            key.append(sentences[0])
        if len(sentences) >= 3:
            key.append(sentences[len(sentences) // 2])
        if len(sentences) >= 2:
            key.append(sentences[-1])

        output += " ".join(s + "." for s in key) + "\n\n"
        output += f"📊 Condensed from {len(sentences)} sentences to {len(key)} key points.\n"
        compression = (1 - len(key) / max(len(sentences), 1)) * 100
        output += f"📉 Compression ratio: **{compression:.0f}%**\n"
    else:
        output += "Please provide text to summarize.\n"

    return output


def _generate_content(text: str) -> str:
    """Generate content based on the topic."""
    clean = re.sub(r'(?i)(write|generate|compose|draft|create|about|please|can you|a|an|the|me)', '', text).strip()

    output = "### Generated Content\n\n"
    output += f"**Topic: {clean.title()}**\n\n"
    output += f"In the realm of {clean.lower()}, we find a fascinating landscape of ideas and possibilities. "
    output += f"The subject of {clean.lower()} has garnered significant attention in recent years, "
    output += f"drawing interest from both experts and enthusiasts alike.\n\n"
    output += f"Key aspects to consider include the fundamental principles that underpin {clean.lower()}, "
    output += f"the current trends shaping its evolution, and the potential future directions it may take. "
    output += f"Understanding these dimensions provides a comprehensive view of the topic.\n\n"
    output += f"💡 *This is a template outline. For production use, integrate with an LLM for richer content generation.*\n"

    return output


def _rewrite(text: str) -> str:
    """Rewrite/improve text."""
    clean = re.sub(r'(?i)(rewrite|improve|polish|rephrase|please|can you|this|:)', '', text).strip()

    output = "### Improved Version\n\n"
    if clean:
        # Simple improvements
        improved = clean[0].upper() + clean[1:] if clean else clean
        improved = re.sub(r'\s+', ' ', improved)
        if not improved.endswith(('.', '!', '?')):
            improved += '.'
        output += f"> {improved}\n\n"
        output += "**Changes made:**\n"
        output += "- ✅ Ensured proper capitalization\n"
        output += "- ✅ Normalized whitespace\n"
        output += "- ✅ Added proper punctuation\n"
    else:
        output += "Please provide text to rewrite.\n"

    return output


config = {
    "author": "naresh@example.com",
    "name": "writing_assistant_agent",
    "description": "Helps with grammar checking, content generation, text summarization, and writing improvement.",
    "deployment": {"url": "http://localhost:3776", "expose": True},
    "skills": [str(PROJECT_ROOT / "skills" / "writing-assistant")],
}

if __name__ == "__main__":
    bindufy(config, handler)
