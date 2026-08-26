"""
Security Review Agent
---------------------
A Bindu microservice that analyses code diffs for security vulnerabilities.

Listens on port 3774.
Called by the orchestrator via A2A.
"""

from __future__ import annotations

import json
import re

from bindu.penguin.bindufy import bindufy

# ---------------------------------------------------------------------------
# Security heuristics
# ---------------------------------------------------------------------------

SECURITY_PATTERNS: list[tuple[str, str, str]] = [
    # (regex, severity, description)
    (r"exec\s*\(", "HIGH", "exec() allows arbitrary code execution"),
    (r"eval\s*\(", "HIGH", "eval() allows arbitrary code execution"),
    (r"os\.system\s*\(", "HIGH", "os.system() exposes shell injection risk"),
    (r"subprocess\.call\s*\(.*shell\s*=\s*True", "HIGH", "shell=True in subprocess is unsafe"),
    (r"pickle\.loads?\s*\(", "HIGH", "pickle deserialization can execute arbitrary code"),
    (r"password\s*=\s*['\"][^'\"]{1,40}['\"]", "HIGH", "Hardcoded password detected"),
    (r"secret\s*=\s*['\"][^'\"]{1,40}['\"]", "HIGH", "Hardcoded secret detected"),
    (r"api_key\s*=\s*['\"][^'\"]{1,40}['\"]", "HIGH", "Hardcoded API key detected"),
    (r"token\s*=\s*['\"][^'\"]{1,40}['\"]", "MEDIUM", "Possible hardcoded token"),
    (r"cursor\.execute\s*\(.*%", "HIGH", "SQL injection risk: use parameterised queries instead of string formatting"),
    (r"SELECT.*WHERE.*\+", "HIGH", "Possible SQL injection via string concatenation"),
    (r"open\s*\(.*['\"]w['\"]", "MEDIUM", "Unrestricted file write – verify path is sanitised"),
    (r"DEBUG\s*=\s*True", "MEDIUM", "DEBUG mode left enabled"),
    (r"verify\s*=\s*False", "MEDIUM", "TLS certificate verification disabled"),
    (r"md5\s*\(", "LOW", "MD5 is cryptographically broken – prefer SHA-256+"),
    (r"sha1\s*\(", "LOW", "SHA-1 is cryptographically weak – prefer SHA-256+"),
    (r"random\.random\s*\(", "LOW", "random.random() is not cryptographically secure – use secrets"),
]


def _scan_diff(diff: str) -> list[dict]:
    """Return a list of findings for every added line in the diff."""
    findings: list[dict] = []
    current_file = "unknown"
    line_number = 0

    for raw_line in diff.splitlines():
        # Track which file we're in
        if raw_line.startswith("+++ b/"):
            current_file = raw_line[6:].strip()
            line_number = 0
            continue
        if raw_line.startswith("@@"):
            # Extract starting line number from hunk header: @@ -a,b +c,d @@
            match = re.search(r"\+(\d+)", raw_line)
            line_number = int(match.group(1)) if match else 0
            continue

        # Only scan added lines (not context or removed)
        if raw_line.startswith("+") and not raw_line.startswith("+++"):
            line_number += 1
            code_line = raw_line[1:]  # strip the leading '+'
            for pattern, severity, description in SECURITY_PATTERNS:
                if re.search(pattern, code_line, re.IGNORECASE):
                    findings.append(
                        {
                            "file": current_file,
                            "line": line_number,
                            "severity": severity,
                            "description": description,
                            "snippet": code_line.strip(),
                        }
                    )
        elif raw_line.startswith(" "):
            line_number += 1

    return findings


def _summarise(findings: list[dict]) -> str:
    if not findings:
        return "✅ No security issues detected in the diff."

    counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
    for f in findings:
        counts[f["severity"]] += 1

    lines = [
        f"🔐 Security scan complete – "
        f"{counts['HIGH']} HIGH, {counts['MEDIUM']} MEDIUM, {counts['LOW']} LOW issue(s) found.\n"
    ]
    for f in findings:
        icon = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🔵"}[f["severity"]]
        lines.append(
            f"{icon} [{f['severity']}] {f['file']}:{f['line']} – {f['description']}\n"
            f"   ```{f['snippet']}```"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Bindu handler
# ---------------------------------------------------------------------------

def handler(messages: list[dict]) -> list[dict]:
    """
    Expects the last user message to contain a JSON payload:
        {"diff": "<unified diff string>"}

    Returns a structured security report.
    """
    last_content = messages[-1].get("content", "") if messages else ""

    # Accept either raw diff or JSON-wrapped diff
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

    findings = _scan_diff(diff)
    report = {
        "agent": "security_agent",
        "total_issues": len(findings),
        "findings": findings,
        "summary": _summarise(findings),
    }

    return [{"role": "assistant", "content": json.dumps(report, indent=2)}]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

config = {
    "author": "contributor@example.com",
    "name": "security_agent",
    "description": (
        "Scans code diffs for security vulnerabilities including hardcoded secrets, "
        "SQL injection, unsafe deserialization, and insecure cryptography."
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
        "url": "http://localhost:3774",
        "expose": True,
    },
    "skills": ["skills/security-scanning"],
}

if __name__ == "__main__":
    bindufy(config, handler)
