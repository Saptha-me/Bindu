"""
Tests for the PR Review Swarm agents.

Run with:
    pytest tests/ -v

Or with coverage (as Bindu project convention):
    pytest -n auto --cov=agents --cov-report=term-missing tests/
"""

from __future__ import annotations

import json
import sys
import os

import pytest

# ---------------------------------------------------------------------------
# Make the agents importable without installing
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agents"))

# We monkey-patch bindufy so the import-time call doesn't start a server
import unittest.mock as mock

with mock.patch("bindu.penguin.bindufy.bindufy", return_value=None):
    pass  # modules will be imported below after patching

# ---------------------------------------------------------------------------
# Fixtures: sample diffs
# ---------------------------------------------------------------------------

CLEAN_DIFF = """\
diff --git a/utils.py b/utils.py
index 0000000..1111111 100644
--- a/utils.py
+++ b/utils.py
@@ -0,0 +1,6 @@
+def add(a: int, b: int) -> int:
+    \"\"\"Return the sum of a and b.\"\"\"
+    return a + b
+
+
+TIMEOUT_SECONDS = 30
"""

SECURITY_BAD_DIFF = """\
diff --git a/auth.py b/auth.py
index 0000000..1111111 100644
--- a/auth.py
+++ b/auth.py
@@ -0,0 +1,10 @@
+import pickle
+import subprocess
+
+def login(user_input):
+    password = "hunter2"
+    cmd = subprocess.call(user_input, shell=True)
+    data = pickle.loads(open("data.pkl", "rb").read())
+    eval(user_input)
+    cursor.execute("SELECT * FROM users WHERE name = '%s'" % user_input)
+    return data
"""

QUALITY_BAD_DIFF = """\
diff --git a/processor.py b/processor.py
index 0000000..1111111 100644
--- a/processor.py
+++ b/processor.py
@@ -0,0 +1,15 @@
+class dataProcessor:
+    def processData(self, inputData):
+        result = []
+        for item in inputData:
+            if item > 42:
+                result.append(item * 99)
+        try:
+            risky()
+        except:
+            pass
+        return result
"""

MIXED_DIFF = SECURITY_BAD_DIFF + "\n" + QUALITY_BAD_DIFF


# ---------------------------------------------------------------------------
# Security agent tests
# ---------------------------------------------------------------------------

class TestSecurityAgent:
    """Unit-tests for security_agent.handler."""

    @pytest.fixture(autouse=True)
    def _import(self):
        with mock.patch("bindu.penguin.bindufy.bindufy"):
            import importlib
            import security_agent as mod
            self.mod = mod

    # helpers
    def _call(self, content: str) -> dict:
        result = self.mod.handler([{"role": "user", "content": content}])
        return json.loads(result[0]["content"])

    # ------------------------------------------------------------------

    def test_clean_diff_no_findings(self):
        report = self._call(CLEAN_DIFF)
        assert report["total_issues"] == 0
        assert "✅" in report["summary"]

    def test_detects_hardcoded_password(self):
        report = self._call(SECURITY_BAD_DIFF)
        severities = [f["severity"] for f in report["findings"]]
        assert "HIGH" in severities

    def test_detects_pickle_loads(self):
        report = self._call(SECURITY_BAD_DIFF)
        messages = [f["description"] for f in report["findings"]]
        assert any("pickle" in m.lower() for m in messages)

    def test_detects_eval(self):
        report = self._call(SECURITY_BAD_DIFF)
        messages = [f["description"] for f in report["findings"]]
        assert any("eval" in m.lower() for m in messages)

    def test_detects_shell_true(self):
        report = self._call(SECURITY_BAD_DIFF)
        messages = [f["description"] for f in report["findings"]]
        assert any("shell" in m.lower() for m in messages)

    def test_detects_sql_injection(self):
        report = self._call(SECURITY_BAD_DIFF)
        messages = [f["description"] for f in report["findings"]]
        assert any("sql" in m.lower() or "parameterised" in m.lower() for m in messages)

    def test_empty_content_returns_error(self):
        report = self._call("")
        assert "error" in report

    def test_json_wrapped_diff(self):
        payload = json.dumps({"diff": SECURITY_BAD_DIFF})
        report = self._call(payload)
        assert report["total_issues"] > 0

    def test_findings_include_file_and_line(self):
        report = self._call(SECURITY_BAD_DIFF)
        for finding in report["findings"]:
            assert "file" in finding
            assert "line" in finding
            assert isinstance(finding["line"], int)

    def test_summary_contains_severity_counts(self):
        report = self._call(SECURITY_BAD_DIFF)
        assert "HIGH" in report["summary"]

    def test_report_structure(self):
        report = self._call(CLEAN_DIFF)
        assert "agent" in report
        assert report["agent"] == "security_agent"
        assert "findings" in report
        assert "summary" in report


# ---------------------------------------------------------------------------
# Quality agent tests
# ---------------------------------------------------------------------------

class TestQualityAgent:
    """Unit-tests for quality_agent.handler."""

    @pytest.fixture(autouse=True)
    def _import(self):
        with mock.patch("bindu.penguin.bindufy.bindufy"):
            import importlib
            import quality_agent as mod
            self.mod = mod

    def _call(self, content: str) -> dict:
        result = self.mod.handler([{"role": "user", "content": content}])
        return json.loads(result[0]["content"])

    # ------------------------------------------------------------------

    def test_clean_diff_no_findings(self):
        report = self._call(CLEAN_DIFF)
        assert report["total_issues"] == 0
        assert "✅" in report["summary"]

    def test_detects_non_pascal_class(self):
        report = self._call(QUALITY_BAD_DIFF)
        categories = [f["category"] for f in report["findings"]]
        assert "naming" in categories

    def test_detects_camel_case_variable(self):
        report = self._call(QUALITY_BAD_DIFF)
        messages = [f["message"] for f in report["findings"]]
        assert any("naming" in f["category"] for f in report["findings"])

    def test_detects_bare_except(self):
        report = self._call(QUALITY_BAD_DIFF)
        categories = [f["category"] for f in report["findings"]]
        assert "error-handling" in categories

    def test_detects_magic_number(self):
        report = self._call(QUALITY_BAD_DIFF)
        categories = [f["category"] for f in report["findings"]]
        assert "style" in categories

    def test_empty_diff_returns_error(self):
        report = self._call("")
        assert "error" in report

    def test_json_wrapped_diff(self):
        payload = json.dumps({"diff": QUALITY_BAD_DIFF})
        report = self._call(payload)
        assert report["total_issues"] > 0

    def test_report_structure(self):
        report = self._call(CLEAN_DIFF)
        assert report["agent"] == "quality_agent"
        assert isinstance(report["findings"], list)

    def test_non_python_files_skipped(self):
        js_diff = QUALITY_BAD_DIFF.replace("processor.py", "processor.js")
        report = self._call(js_diff)
        # JS file should produce 0 findings (Python-only checks)
        assert report["total_issues"] == 0


# ---------------------------------------------------------------------------
# Orchestrator unit tests (sub-agents mocked)
# ---------------------------------------------------------------------------

class TestOrchestrator:
    """Unit-tests for orchestrator.handler with mocked sub-agents."""

    @pytest.fixture(autouse=True)
    def _import(self):
        with mock.patch("bindu.penguin.bindufy.bindufy"):
            import importlib
            import orchestrator as mod
            self.mod = mod

    def _mock_reports(self, sec_report: dict, qual_report: dict):
        """Return a context manager that mocks both _call_agent calls."""
        def fake_call_agent(url: str, diff: str) -> dict:
            if "3774" in url:
                return sec_report
            return qual_report

        return mock.patch.object(self.mod, "_call_agent", side_effect=fake_call_agent)

    def _call(self, content: str, sec_report: dict, qual_report: dict) -> dict:
        with self._mock_reports(sec_report, qual_report):
            result = self.mod.handler([{"role": "user", "content": content}])
        return json.loads(result[0]["content"])

    # ------------------------------------------------------------------

    CLEAN_SEC  = {"agent": "security_agent", "total_issues": 0, "findings": [], "summary": "✅ No issues."}
    CLEAN_QUAL = {"agent": "quality_agent",  "total_issues": 0, "findings": [], "summary": "✅ No issues."}
    HIGH_SEC   = {
        "agent": "security_agent",
        "total_issues": 1,
        "findings": [{"severity": "HIGH", "description": "eval()", "file": "x.py", "line": 1}],
        "summary": "🔐 1 HIGH issue.",
    }

    def test_clean_diff_lgtm_verdict(self):
        report = self._call(CLEAN_DIFF, self.CLEAN_SEC, self.CLEAN_QUAL)
        assert "LGTM" in report["verdict"]

    def test_high_security_issue_blocks_merge(self):
        report = self._call(MIXED_DIFF, self.HIGH_SEC, self.CLEAN_QUAL)
        assert "BLOCK" in report["verdict"]

    def test_report_contains_markdown(self):
        report = self._call(CLEAN_DIFF, self.CLEAN_SEC, self.CLEAN_QUAL)
        assert "report_markdown" in report
        assert "PR Review Swarm" in report["report_markdown"]

    def test_report_nested_structure(self):
        report = self._call(CLEAN_DIFF, self.CLEAN_SEC, self.CLEAN_QUAL)
        assert "security" in report
        assert "quality" in report
        assert report["agent"] == "orchestrator"

    def test_empty_input_returns_error(self):
        with self._mock_reports(self.CLEAN_SEC, self.CLEAN_QUAL):
            result = self.mod.handler([{"role": "user", "content": ""}])
        parsed = json.loads(result[0]["content"])
        assert "error" in parsed

    def test_json_wrapped_diff_accepted(self):
        payload = json.dumps({"diff": CLEAN_DIFF})
        report = self._call(payload, self.CLEAN_SEC, self.CLEAN_QUAL)
        assert report["agent"] == "orchestrator"

    def test_invalid_github_url_returns_error(self):
        with mock.patch.object(
            self.mod, "_fetch_github_diff", return_value=(None, "PR not found")
        ):
            result = self.mod.handler([
                {"role": "user", "content": "https://github.com/bad/repo/pull/9999"}
            ])
        parsed = json.loads(result[0]["content"])
        assert "error" in parsed

    def test_parallel_execution_both_agents_called(self):
        called = []

        def spy(url: str, diff: str) -> dict:
            called.append(url)
            return self.CLEAN_SEC if "3774" in url else self.CLEAN_QUAL

        with mock.patch.object(self.mod, "_call_agent", side_effect=spy):
            self.mod.handler([{"role": "user", "content": CLEAN_DIFF}])

        assert len(called) == 2
        assert any("3774" in u for u in called)
        assert any("3775" in u for u in called)


# ---------------------------------------------------------------------------
# Integration-style tests (handler-to-handler, no network)
# ---------------------------------------------------------------------------

class TestEndToEnd:
    """
    Full-stack tests: pass a diff through the real security and quality
    handlers, then feed their outputs into the orchestrator's merge logic.
    """

    @pytest.fixture(autouse=True)
    def _import(self):
        with mock.patch("bindu.penguin.bindufy.bindufy"):
            import security_agent as sec
            import quality_agent  as qual
            import orchestrator   as orch
            self.sec  = sec
            self.qual = qual
            self.orch = orch

    def _full_review(self, diff: str) -> dict:
        """Run all three handlers without any network calls."""
        sec_msg  = self.sec.handler( [{"role": "user", "content": json.dumps({"diff": diff})}])
        qual_msg = self.qual.handler([{"role": "user", "content": json.dumps({"diff": diff})}])

        sec_report  = json.loads(sec_msg[0]["content"])
        qual_report = json.loads(qual_msg[0]["content"])

        def fake_call_agent(url: str, _diff: str) -> dict:
            return sec_report if "3774" in url else qual_report

        with mock.patch.object(self.orch, "_call_agent", side_effect=fake_call_agent):
            result = self.orch.handler([{"role": "user", "content": diff}])
        return json.loads(result[0]["content"])

    def test_clean_code_passes(self):
        report = self._full_review(CLEAN_DIFF)
        assert "LGTM" in report["verdict"]
        assert report["security"]["total_issues"] == 0
        assert report["quality"]["total_issues"] == 0

    def test_dangerous_code_blocked(self):
        report = self._full_review(SECURITY_BAD_DIFF)
        assert "BLOCK" in report["verdict"]

    def test_quality_issues_flagged(self):
        report = self._full_review(QUALITY_BAD_DIFF)
        assert report["quality"]["total_issues"] > 0

    def test_mixed_diff_comprehensive(self):
        report = self._full_review(MIXED_DIFF)
        # Should block on security
        assert "BLOCK" in report["verdict"]
        # Should also surface quality issues
        assert report["quality"]["total_issues"] > 0
        # Markdown report should be generated
        assert len(report["report_markdown"]) > 100
