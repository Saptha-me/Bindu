"""
Code Quality Agent
------------------
A Bindu microservice that reviews code diffs for style, complexity,
maintainability, and Pythonic best practices.

Listens on port 3775.
Called by the orchestrator via A2A.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Quality heuristics
# ---------------------------------------------------------------------------

@dataclass
class QualityIssue:
    file: str
    line: int
    category: str   # e.g. "complexity", "naming", "style"
    message: str
    suggestion: str
    snippet: str = ""


def _check_function_length(lines: list[str], filename: str) -> list[QualityIssue]:
    """Flag functions / methods longer than 40 lines."""
    issues: list[QualityIssue] = []
    func_start: int | None = None
    func_name = ""
    depth = 0

    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if re.match(r"^(async\s+)?def\s+\w+", stripped):
            if func_start is not None and (i - func_start) > 40:
                issues.append(
                    QualityIssue(
                        file=filename,
                        line=func_start,
                        category="complexity",
                        message=f"Function `{func_name}` is {i - func_start} lines long (>40).",
                        suggestion="Consider splitting into smaller, single-responsibility functions.",
                    )
                )
            func_start = i
            match = re.search(r"def\s+(\w+)", stripped)
            func_name = match.group(1) if match else "unknown"

    return issues


def _check_naming(lines: list[str], filename: str) -> list[QualityIssue]:
    """Flag non-snake_case variable names and non-PascalCase class names."""
    issues: list[QualityIssue] = []
    for i, line in enumerate(lines, start=1):
        stripped = line.lstrip()
        # Class not in PascalCase
        cls_match = re.match(r"^class\s+([a-z]\w*)\s*[:\(]", stripped)
        if cls_match:
            issues.append(
                QualityIssue(
                    file=filename,
                    line=i,
                    category="naming",
                    message=f"Class `{cls_match.group(1)}` should use PascalCase.",
                    suggestion=f"Rename to `{cls_match.group(1).title()}`.",
                    snippet=stripped[:80],
                )
            )
        # Variable assigned in camelCase (heuristic: mixed case, not ALL_CAPS)
        var_match = re.match(r"^([a-z]+[A-Z]\w*)\s*=", stripped)
        if var_match and not var_match.group(1).isupper():
            issues.append(
                QualityIssue(
                    file=filename,
                    line=i,
                    category="naming",
                    message=f"Variable `{var_match.group(1)}` appears to use camelCase.",
                    suggestion="PEP 8 recommends snake_case for variable names.",
                    snippet=stripped[:80],
                )
            )
    return issues


def _check_magic_numbers(lines: list[str], filename: str) -> list[QualityIssue]:
    """Flag bare numeric literals that look like magic numbers."""
    issues: list[QualityIssue] = []
    for i, line in enumerate(lines, start=1):
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("\"\"\""):
            continue
        if re.match(r"^[A-Z][A-Z0-9_]+\s*=\s*\d+", stripped):
            continue
        matches = re.findall(r"(?<!\w)(\d{2,})(?!\w)", stripped)
        for num in matches:
            if int(num) not in {10, 100, 1000}:  # very common, low-signal
                issues.append(
                    QualityIssue(
                        file=filename,
                        line=i,
                        category="style",
                        message=f"Magic number `{num}` found.",
                        suggestion="Extract into a named constant for readability.",
                        snippet=stripped[:80],
                    )
                )
    return issues


def _check_missing_docstrings(lines: list[str], filename: str) -> list[QualityIssue]:
    """Flag public functions/classes without a docstring."""
    issues: list[QualityIssue] = []
    for i, line in enumerate(lines[:-1], start=1):
        stripped = line.strip()
        if re.match(r"^(async\s+)?def\s+[^_]", stripped) or re.match(r"^class\s+[^_]", stripped):
            next_stripped = lines[i].strip() if i < len(lines) else ""
            if not next_stripped.startswith('"""') and not next_stripped.startswith("'''"):
                match = re.search(r"(?:def|class)\s+(\w+)", stripped)
                name = match.group(1) if match else "unknown"
                issues.append(
                    QualityIssue(
                        file=filename,
                        line=i,
                        category="documentation",
                        message=f"`{name}` is missing a docstring.",
                        suggestion='Add a brief """docstring""" describing purpose, args, and return value.',
                        snippet=stripped[:80],
                    )
                )
    return issues


def _check_bare_excepts(lines: list[str], filename: str) -> list[QualityIssue]:
    issues: list[QualityIssue] = []
    for i, line in enumerate(lines, start=1):
        if re.match(r"\s*except\s*:", line):
            issues.append(
                QualityIssue(
                    file=filename,
                    line=i,
                    category="error-handling",
                    message="Bare `except:` clause catches everything including SystemExit.",
                    suggestion="Use `except Exception:` or a more specific exception type.",
                    snippet=line.strip(),
                )
            )
    return issues


def _analyse_diff(diff: str) -> list[QualityIssue]:
    """Extract added lines per file and run all checks."""
    all_issues: list[QualityIssue] = []
    current_file = "unknown"
    added_lines: dict[str, list[str]] = {}
    line_offset: dict[str, int] = {}

    for raw_line in diff.splitlines():
        if raw_line.startswith("+++ b/"):
            current_file = raw_line[6:].strip()
            added_lines.setdefault(current_file, [])
        elif raw_line.startswith("@@"):
            match = re.search(r"\+(\d+)", raw_line)
            line_offset[current_file] = int(match.group(1)) if match else 1
        elif raw_line.startswith("+") and not raw_line.startswith("+++"):
            added_lines.setdefault(current_file, []).append(raw_line[1:])
        elif raw_line.startswith(" "):
            added_lines.setdefault(current_file, []).append(raw_line[1:])

    for filename, lines in added_lines.items():
        if filename.endswith(".py"):
            all_issues += _check_function_length(lines, filename)
            all_issues += _check_naming(lines, filename)
            all_issues += _check_magic_numbers(lines, filename)
            all_issues += _check_missing_docstrings(lines, filename)
            all_issues += _check_bare_excepts(lines, filename)

    return all_issues


def _summarise(issues: list[QualityIssue]) -> str:
    if not issues:
        return "✅ Code quality looks great! No issues found in the diff."

    category_counts: dict[str, int] = {}
    for issue in issues:
        category_counts[issue.category] = category_counts.get(issue.category, 0) + 1

    summary_line = "📋 Quality review: " + ", ".join(
        f"{v} {k}" for k, v in category_counts.items()
    ) + f" ({len(issues)} total issues)\n"

    lines = [summary_line]
    for issue in issues:
        lines.append(
            f"🔸 [{issue.category.upper()}] {issue.file}:{issue.line} – {issue.message}\n"
            f"   💡 {issue.suggestion}"
            + (f"\n   ```{issue.snippet}```" if issue.snippet else "")
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Bindu handler
# ---------------------------------------------------------------------------

def handler(messages: list[dict]) -> list[dict]:
    """
    Expects the last user message to contain:
        {"diff": "<unified diff string>"}
    """
    last_content = messages[-1].get("content", "") if messages else ""

    try:
        payload = json.loads(last_content)
        diff = payload.get("diff", last_content)
    except (json.JSONDecodeError, AttributeError):
        diff = last_content

    if not diff or diff.strip() == "":
        return [
            {
                "role": "assistant",
                "content": json.dumps(
                    {"error": "No diff provided. Send {\"diff\": \"<unified diff>\"}"},
                    indent=2,
                ),
            }
        ]

    issues = _analyse_diff(diff)
    report = {
        "agent": "quality_agent",
        "total_issues": len(issues),
        "findings": [
            {
                "file": i.file,
                "line": i.line,
                "category": i.category,
                "message": i.message,
                "suggestion": i.suggestion,
                "snippet": i.snippet,
            }
            for i in issues
        ],
        "summary": _summarise(issues),
    }

    return [{"role": "assistant", "content": json.dumps(report, indent=2)}]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

config = {
    "author": "contributor@example.com",
    "name": "quality_agent",
    "description": (
        "Reviews code diffs for style violations, naming conventions, magic numbers, "
        "missing docstrings, bare excepts, and function length."
    ),
    "version": "1.0.0",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
    },
    "auth": {"enabled": False},
    "storage": {"type": "memory"},
    "scheduler": {"type": "memory"},
    "deployment": {
        "url": "http://localhost:3775",
        "expose": True,
    },
    "skills": ["skills/code-quality"],
}

if __name__ == "__main__":
    bindufy(config, handler)
