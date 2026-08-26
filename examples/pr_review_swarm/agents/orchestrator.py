"""
PR Review Orchestrator Agent
-----------------------------
The entry-point Bindu microservice for the PR Review Swarm.

Given a GitHub PR URL (or a raw unified diff), the orchestrator:
  1. Fetches the PR diff from GitHub (unauthenticated for public repos).
  2. Fans out to the Security Agent  (port 3774) via A2A.
  3. Fans out to the Quality Agent   (port 3775) via A2A.
  4. Merges the reports and returns a single structured review.

This is a live demonstration of agent-to-agent collaboration on Bindu.
Listens on port 3773.
"""

from __future__ import annotations

import concurrent.futures
import json
import re
import urllib.error
import urllib.request
from typing import Any

from bindu.penguin.bindufy import bindufy

# ---------------------------------------------------------------------------
# Configuration – addresses of the peer Bindu agents
# ---------------------------------------------------------------------------

SECURITY_AGENT_URL = "http://localhost:3774/messages"
QUALITY_AGENT_URL  = "http://localhost:3775/messages"

GITHUB_RAW_DIFF_HEADERS = {
    "Accept": "application/vnd.github.v3.diff",
    "User-Agent": "bindu-pr-review-swarm/1.0",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pr_url_to_diff_url(pr_url: str) -> str | None:
    """
    Convert a GitHub PR URL to its diff API endpoint.

    Supports:
      https://github.com/owner/repo/pull/123
      https://github.com/owner/repo/pull/123/files
    """
    match = re.match(
        r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)",
        pr_url.strip(),
    )
    if not match:
        return None
    owner, repo, pr_number = match.groups()
    return f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"


def _fetch_github_diff(pr_url: str) -> tuple[str | None, str | None]:
    """
    Fetch a unified diff from GitHub.
    Returns (diff_text, error_message).
    """
    api_url = _pr_url_to_diff_url(pr_url)
    if api_url is None:
        return None, f"Could not parse GitHub PR URL: {pr_url!r}"

    request = urllib.request.Request(api_url, headers=GITHUB_RAW_DIFF_HEADERS)
    try:
        with urllib.request.urlopen(request, timeout=10) as resp:
            return resp.read().decode("utf-8", errors="replace"), None
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None, "PR not found – make sure the repo is public and the PR number is correct."
        if e.code == 403:
            return None, "GitHub rate limit hit. Pass a personal diff directly instead of a URL."
        return None, f"GitHub returned HTTP {e.code}."
    except urllib.error.URLError as e:
        return None, f"Network error fetching diff: {e.reason}"


def _call_agent(agent_url: str, diff: str) -> dict:
    """
    Send a diff to a peer Bindu agent via A2A and return its parsed report.
    Falls back to an error dict if the call fails.
    """
    payload = json.dumps([{"role": "user", "content": json.dumps({"diff": diff})}]).encode()
    request = urllib.request.Request(
        agent_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            messages = json.loads(raw)
            # The agent returns a messages array; pull out the last assistant message
            content = next(
                (m["content"] for m in reversed(messages) if m.get("role") == "assistant"),
                raw,
            )
            return json.loads(content)
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc), "agent": agent_url}


def _overall_verdict(security_report: dict, quality_report: dict) -> str:
    """Derive a simple PASS / NEEDS WORK / BLOCK verdict."""
    sec_findings = security_report.get("findings", [])
    has_high_sec = any(f.get("severity") == "HIGH" for f in sec_findings)
    quality_issues = quality_report.get("total_issues", 0)

    if has_high_sec:
        return "🚫 BLOCK – High-severity security issue(s) must be fixed before merge."
    if sec_findings or quality_issues > 5:
        return "⚠️  NEEDS WORK – Review issues before merging."
    return "✅ LGTM – Minor issues only. Safe to merge after addressing suggestions."


def _build_markdown_report(
    pr_source: str,
    security_report: dict,
    quality_report: dict,
) -> str:
    """Compose a human-readable Markdown review summary."""
    verdict = _overall_verdict(security_report, quality_report)

    sec_summary  = security_report.get("summary", "_No summary available._")
    qual_summary = quality_report.get("summary", "_No summary available._")

    return f"""# 🤖 PR Review Swarm Report

**Source:** `{pr_source}`
**Verdict:** {verdict}

---

## 🔐 Security Review  _(security_agent @ :3774)_

{sec_summary}

---

## 📋 Code Quality Review  _(quality_agent @ :3775)_

{qual_summary}

---

_Generated by the **Bindu PR Review Swarm** – three agents, one review._
_Security Agent · Quality Agent · Orchestrator_
"""


# ---------------------------------------------------------------------------
# Bindu handler
# ---------------------------------------------------------------------------

def handler(messages: list[dict]) -> list[dict]:
    """
    Accepts one of:
      • A GitHub PR URL:  "https://github.com/owner/repo/pull/123"
      • A raw unified diff (starts with "diff --git" or "---")
      • JSON: {"pr_url": "..."} or {"diff": "..."}
    """
    last_content = messages[-1].get("content", "") if messages else ""

    # --- Parse input ---
    diff: str | None = None
    pr_source = "raw diff"
    error: str | None = None

    try:
        payload = json.loads(last_content)
    except (json.JSONDecodeError, TypeError):
        payload = {}

    if isinstance(payload, dict) and "pr_url" in payload:
        pr_source = payload["pr_url"]
        diff, error = _fetch_github_diff(pr_source)
    elif isinstance(payload, dict) and "diff" in payload:
        diff = payload["diff"]
    elif isinstance(last_content, str) and last_content.strip().startswith("https://github.com"):
        pr_source = last_content.strip()
        diff, error = _fetch_github_diff(pr_source)
    else:
        # Assume raw diff text
        diff = last_content

    if error:
        return [{"role": "assistant", "content": json.dumps({"error": error}, indent=2)}]

    if not diff or not diff.strip():
        return [
            {
                "role": "assistant",
                "content": json.dumps(
                    {
                        "error": (
                            "No diff found. Send a GitHub PR URL "
                            "or a unified diff as the message content."
                        )
                    },
                    indent=2,
                ),
            }
        ]

    # --- Fan out to sub-agents in parallel ---
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_sec  = executor.submit(_call_agent, SECURITY_AGENT_URL, diff)
        future_qual = executor.submit(_call_agent, QUALITY_AGENT_URL,  diff)
        security_report = future_sec.result()
        quality_report  = future_qual.result()

    # --- Compose final report ---
    markdown_report = _build_markdown_report(pr_source, security_report, quality_report)

    response_payload = {
        "agent": "orchestrator",
        "source": pr_source,
        "verdict": _overall_verdict(security_report, quality_report),
        "security": security_report,
        "quality": quality_report,
        "report_markdown": markdown_report,
    }

    return [{"role": "assistant", "content": json.dumps(response_payload, indent=2)}]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

config = {
    "author": "contributor@example.com",
    "name": "pr_review_orchestrator",
    "description": (
        "Orchestrates a multi-agent PR review swarm. "
        "Accepts a GitHub PR URL or a unified diff and returns a "
        "combined security + quality report by coordinating with "
        "security_agent (:3774) and quality_agent (:3775)."
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
        "url": "http://localhost:3773",
        "expose": True,
    },
    "skills": [
        "skills/question-answering",
        "skills/code-review",
    ],
}

if __name__ == "__main__":
    bindufy(config, handler)
