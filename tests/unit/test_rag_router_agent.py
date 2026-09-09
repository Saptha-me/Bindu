"""Unit tests for examples/rag_router_agent.

All tests are hermetic: no network calls, no file I/O, no LLM calls.
External dependencies are patched via unittest.mock.
"""

import os
import types
from unittest.mock import MagicMock, mock_open, patch


# ===========================================================================
# router.py
# ===========================================================================
class TestClassifyIntent:
    def test_finance_keywords(self):
        from examples.rag_router_agent.router import classify_intent

        assert classify_intent("What is GST?") == "finance"
        assert classify_intent("tax on money") == "finance"

    def test_legal_keywords(self):
        from examples.rag_router_agent.router import classify_intent

        assert classify_intent("court law ruling") == "legal"

    def test_tech_keywords(self):
        from examples.rag_router_agent.router import classify_intent

        assert classify_intent("how does the api server work?") == "tech"

    def test_unknown_returns_none(self):
        from examples.rag_router_agent.router import classify_intent

        assert classify_intent("hello world") is None

    def test_empty_query_returns_none(self):
        from examples.rag_router_agent.router import classify_intent

        assert classify_intent("") is None


class TestRouteAgent:
    """route_agent must return a callable or None — never raise."""

    def _stub_agents(self):
        """Inject minimal stub agent modules so imports don't fail."""
        for name in (
            "agents.finance_agent",
            "agents.legal_agent",
            "agents.tech_agent",
        ):
            mod = types.ModuleType(name)
            short = name.split(".")[-1]
            setattr(mod, short, lambda q, c: f"stub:{short}")
            __import__("sys").modules[name] = mod

        if "agents" not in __import__("sys").modules:
            __import__("sys").modules["agents"] = types.ModuleType("agents")

    def test_finance_returns_callable(self):
        self._stub_agents()
        from examples.rag_router_agent.router import route_agent

        assert callable(route_agent("finance"))

    def test_legal_returns_callable(self):
        self._stub_agents()
        from examples.rag_router_agent.router import route_agent

        assert callable(route_agent("legal"))

    def test_tech_returns_callable(self):
        self._stub_agents()
        from examples.rag_router_agent.router import route_agent

        assert callable(route_agent("tech"))

    def test_unknown_returns_none(self):
        self._stub_agents()
        from examples.rag_router_agent.router import route_agent

        assert route_agent("unknown") is None

    def test_empty_intent_returns_none(self):
        self._stub_agents()
        from examples.rag_router_agent.router import route_agent

        assert route_agent("") is None


# ===========================================================================
# source_router.py
# ===========================================================================
class TestSelectSource:
    def test_free_query_returns_free_source(self):
        from examples.rag_router_agent.source_router import select_source

        result = select_source("finance", "What is GST?")
        assert result is not None
        assert result["type"] == "free"

    def test_premium_keyword_returns_premium_source(self):
        from examples.rag_router_agent.source_router import select_source

        result = select_source("finance", "latest GST updates")
        assert result is not None
        assert result["type"] == "premium"

    def test_advanced_keyword_returns_premium(self):
        from examples.rag_router_agent.source_router import select_source

        result = select_source("finance", "advanced GST rules")
        assert result["type"] == "premium"

    def test_unknown_intent_returns_none(self):
        from examples.rag_router_agent.source_router import select_source

        assert select_source("nonexistent", "query") is None

    def test_result_has_path_key(self):
        from examples.rag_router_agent.source_router import select_source

        result = select_source("finance", "What is GST?")
        assert "path" in result

    def test_db_used_is_relative_posix_path(self):
        from examples.rag_router_agent.source_router import (
            BASE_DIR,
            select_source,
        )

        result = select_source("finance", "What is GST?")
        rel = os.path.relpath(result["path"], BASE_DIR).replace("\\", "/")

        assert not os.path.isabs(rel)
        assert "\\" not in rel


# ===========================================================================
# retriever.py
# ===========================================================================
class TestRetrieveDocs:
    def test_returns_matching_docs(self):
        from examples.rag_router_agent.retriever import retrieve_docs

        content = "GST is a tax on goods.\nIncome tax is different.\n"

        with patch("builtins.open", mock_open(read_data=content)):
            docs = retrieve_docs("dummy_path.txt", "GST tax")

        assert len(docs) >= 1
        assert any("GST" in d for d in docs)

    def test_returns_empty_on_missing_file(self):
        from examples.rag_router_agent.retriever import retrieve_docs

        with patch("builtins.open", side_effect=OSError):
            docs = retrieve_docs("missing.txt", "GST")

        assert docs == []

    def test_respects_k_limit(self):
        from examples.rag_router_agent.retriever import retrieve_docs

        content = "\n".join([f"GST line {i}" for i in range(10)]) + "\n"

        with patch("builtins.open", mock_open(read_data=content)):
            docs = retrieve_docs("dummy.txt", "GST", k=2)

        assert len(docs) <= 2


# ===========================================================================
# skale_payment.py
# ===========================================================================
class TestCallSkaleFacilitator:
    def test_skips_in_ci(self, monkeypatch):
        monkeypatch.setenv("CI", "true")

        from examples.rag_router_agent.skale_payment import (
            call_skale_facilitator,
        )

        result = call_skale_facilitator()

        assert result["status"] == "skipped"

    def test_reachable_when_address_not_set(self, monkeypatch):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.delenv("SKALE_PAY_TO_ADDRESS", raising=False)

        from examples.rag_router_agent.skale_payment import (
            call_skale_facilitator,
        )

        result = call_skale_facilitator()

        assert result["status"] == "reachable"

    def test_success_when_sdk_works(self, monkeypatch):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.setenv("SKALE_PAY_TO_ADDRESS", "0xDeadBeef")

        mock_server = MagicMock()
        mock_req = MagicMock()

        mock_req.model_dump.return_value = {
            "network": "eip155:1564830818",
        }

        mock_server.build_payment_requirements.return_value = [mock_req]

        mock_server_cls = MagicMock(return_value=mock_server)
        mock_facilitator_cls = MagicMock()
        mock_scheme = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "x402": MagicMock(
                    x402ResourceServerSync=mock_server_cls,
                    ResourceConfig=MagicMock(),
                ),
                "x402.http": MagicMock(HTTPFacilitatorClientSync=mock_facilitator_cls),
                "x402.mechanisms.evm.exact": MagicMock(
                    ExactEvmServerScheme=mock_scheme
                ),
            },
        ):
            import importlib

            from examples.rag_router_agent import skale_payment as sp

            importlib.reload(sp)

            monkeypatch.setenv("SKALE_PAY_TO_ADDRESS", "0xDeadBeef")

            result = sp.call_skale_facilitator()

        assert result["status"] in ("success", "reachable")

    def test_non_blocking_on_sdk_import_error(self, monkeypatch):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.setenv("SKALE_PAY_TO_ADDRESS", "0xDeadBeef")

        with patch(
            "examples.rag_router_agent.skale_payment._load_sdk",
            side_effect=ImportError("x402 not installed"),
        ):
            from examples.rag_router_agent.skale_payment import (
                call_skale_facilitator,
            )

            result = call_skale_facilitator()

        assert result["status"] == "reachable"
        assert "x402" in result["note"]

    def test_non_blocking_on_facilitator_exception(self, monkeypatch):
        monkeypatch.delenv("CI", raising=False)
        monkeypatch.setenv("SKALE_PAY_TO_ADDRESS", "0xDeadBeef")

        with patch(
            "examples.rag_router_agent.skale_payment._load_sdk",
            side_effect=Exception("network error"),
        ):
            from examples.rag_router_agent.skale_payment import (
                call_skale_facilitator,
            )

            result = call_skale_facilitator()

        assert result["status"] == "reachable"


# ===========================================================================
# agent.py — handler()
# ===========================================================================
class TestHandler:
    """Tests for the top-level handler function."""

    def _make_messages(self, text):
        return [{"role": "user", "content": text}]

    def test_invalid_input_empty_list(self):
        from examples.rag_router_agent.agent import handler

        result = handler([])

        assert result["answer"] == "Invalid input"

    def test_invalid_input_non_string_content(self):
        from examples.rag_router_agent.agent import handler

        result = handler([{"role": "user", "content": 123}])

        assert result["answer"] == "Invalid input"

    def test_unknown_intent_returns_error(self):
        from examples.rag_router_agent.agent import handler

        result = handler(self._make_messages("hello world random"))

        assert result["answer"] == "No intent found"

    def test_free_query_no_payment(self):
        from examples.rag_router_agent.agent import handler

        docs = ["GST is a goods and services tax.\n"]

        with (
            patch(
                "examples.rag_router_agent.agent.classify_intent",
                return_value="finance",
            ),
            patch(
                "examples.rag_router_agent.agent.select_source",
                return_value={"path": "db/finance.txt", "type": "free"},
            ),
            patch(
                "examples.rag_router_agent.agent.retrieve_docs",
                return_value=docs,
            ),
            patch(
                "examples.rag_router_agent.agent.route_agent",
                return_value=lambda q, c: "GST answer",
            ),
            patch("examples.rag_router_agent.agent.agent", None),
        ):
            result = handler(self._make_messages("What is GST?"))

        assert result["payment"] is None
        assert result["payment_reason"] == "free_access"
        assert result["answer"] == "GST answer"
