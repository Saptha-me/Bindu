"""Tests for MiniMax AI example agent configuration.

Validates the MiniMax example follows Bindu patterns correctly and
that the OpenAI-compatible integration is properly configured.
"""

import ast
import os
from pathlib import Path

import pytest

# Path to the example file
EXAMPLE_PATH = (
    Path(__file__).parent.parent.parent / "examples" / "beginner" / "minimax_example.py"
)
ENV_EXAMPLE_PATH = (
    Path(__file__).parent.parent.parent / "examples" / "beginner" / ".env.example"
)


class TestMiniMaxExampleFile:
    """Test MiniMax example file structure and content."""

    def test_example_file_exists(self):
        """Verify the MiniMax example file exists."""
        assert EXAMPLE_PATH.exists(), f"Missing: {EXAMPLE_PATH}"

    def test_example_is_valid_python(self):
        """Verify the example is valid Python syntax."""
        source = EXAMPLE_PATH.read_text()
        tree = ast.parse(source, filename=str(EXAMPLE_PATH))
        assert tree is not None

    def test_example_has_docstring(self):
        """Verify the example has a module docstring."""
        source = EXAMPLE_PATH.read_text()
        tree = ast.parse(source)
        docstring = ast.get_docstring(tree)
        assert docstring is not None
        assert "MiniMax" in docstring

    def test_example_imports_bindufy(self):
        """Verify the example imports bindufy."""
        source = EXAMPLE_PATH.read_text()
        assert "from bindu.penguin.bindufy import bindufy" in source

    def test_example_imports_openailike(self):
        """Verify the example uses OpenAILike for MiniMax."""
        source = EXAMPLE_PATH.read_text()
        assert "from agno.models.openai import OpenAILike" in source

    def test_example_has_minimax_base_url(self):
        """Verify the example uses the correct MiniMax API URL."""
        source = EXAMPLE_PATH.read_text()
        assert "https://api.minimax.io/v1" in source

    def test_example_uses_minimax_m3(self):
        """Verify the example uses MiniMax-M3 model."""
        source = EXAMPLE_PATH.read_text()
        assert "MiniMax-M3" in source

    def test_example_reads_api_key_from_env(self):
        """Verify the example reads MINIMAX_API_KEY from env."""
        source = EXAMPLE_PATH.read_text()
        assert "MINIMAX_API_KEY" in source
        assert 'os.getenv("MINIMAX_API_KEY")' in source

    def test_example_has_config_dict(self):
        """Verify the example has a config dictionary with required fields."""
        source = EXAMPLE_PATH.read_text()
        assert '"name"' in source
        assert '"author"' in source
        assert '"description"' in source
        assert '"deployment"' in source

    def test_example_has_handler_function(self):
        """Verify the example defines a handler function."""
        source = EXAMPLE_PATH.read_text()
        assert "def handler(" in source

    def test_example_calls_bindufy(self):
        """Verify the example calls bindufy."""
        source = EXAMPLE_PATH.read_text()
        assert "bindufy(config, handler)" in source

    def test_example_has_main_guard(self):
        """Verify the example has __main__ guard."""
        source = EXAMPLE_PATH.read_text()
        assert 'if __name__ == "__main__":' in source

    def test_example_uses_duckduckgo_tools(self):
        """Verify the example includes search tools."""
        source = EXAMPLE_PATH.read_text()
        assert "DuckDuckGoTools" in source

    def test_example_loads_dotenv(self):
        """Verify the example loads .env file."""
        source = EXAMPLE_PATH.read_text()
        assert "load_dotenv()" in source


class TestEnvExampleFile:
    """Test that .env.example includes MiniMax configuration."""

    def test_env_example_has_minimax_key(self):
        """Verify .env.example includes MINIMAX_API_KEY."""
        content = ENV_EXAMPLE_PATH.read_text()
        assert "MINIMAX_API_KEY" in content

    def test_env_example_has_minimax_section(self):
        """Verify .env.example has a MiniMax section header."""
        content = ENV_EXAMPLE_PATH.read_text()
        assert "MiniMax" in content

    def test_env_example_has_platform_url(self):
        """Verify .env.example references the MiniMax platform."""
        content = ENV_EXAMPLE_PATH.read_text()
        assert "platform.minimaxi.com" in content


class TestMiniMaxModelConstants:
    """Test MiniMax model constants and values."""

    def test_valid_minimax_models(self):
        """Verify known MiniMax model identifiers."""
        valid_models = {
            "MiniMax-M3",
            "MiniMax-M2.7",
            "MiniMax-M2.7-highspeed",
        }
        # Parse the example to check the model used
        source = EXAMPLE_PATH.read_text()
        for model in valid_models:
            # At least M3 should be referenced
            if model == "MiniMax-M3":
                assert model in source

    def test_minimax_api_url_format(self):
        """Verify MiniMax API URL follows OpenAI-compatible format."""
        source = EXAMPLE_PATH.read_text()
        # Should end with /v1 (OpenAI-compatible pattern)
        assert "api.minimax.io/v1" in source

    def test_example_does_not_hardcode_api_key(self):
        """Verify no API key is hardcoded in the example."""
        source = EXAMPLE_PATH.read_text()
        # Should use os.getenv, not a hardcoded string
        assert "sk-" not in source.replace("sk-or-v1", "")  # exclude OpenRouter pattern
        assert 'api_key="' not in source


class TestReadmeUpdates:
    """Test that README files mention MiniMax."""

    def test_main_readme_mentions_minimax(self):
        """Verify main README mentions MiniMax."""
        readme = (Path(__file__).parent.parent.parent / "README.md").read_text(encoding="utf-8")
        assert "MiniMax" in readme

    def test_main_readme_has_minimax_api_key(self):
        """Verify main README mentions MINIMAX_API_KEY."""
        readme = (Path(__file__).parent.parent.parent / "README.md").read_text(encoding="utf-8")
        assert "MINIMAX_API_KEY" in readme

    def test_examples_readme_mentions_minimax(self):
        """Verify examples README lists the MiniMax example."""
        readme = (
            Path(__file__).parent.parent.parent / "examples" / "README.md"
        ).read_text(encoding="utf-8")
        assert "minimax_example.py" in readme

    def test_examples_readme_mentions_minimax_env(self):
        """Verify examples README mentions MINIMAX_API_KEY in env vars."""
        readme = (
            Path(__file__).parent.parent.parent / "examples" / "README.md"
        ).read_text(encoding="utf-8")
        assert "MINIMAX_API_KEY" in readme


class TestMiniMaxIntegration:
    """Integration tests for MiniMax API (require MINIMAX_API_KEY)."""

    @pytest.fixture
    def api_key(self):
        key = os.getenv("MINIMAX_API_KEY")
        if not key:
            pytest.skip("MINIMAX_API_KEY not set")
        return key

    def test_minimax_api_connection(self, api_key):
        """Test that MiniMax API is reachable with valid key."""
        import httpx

        resp = httpx.post(
            "https://api.minimax.io/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "MiniMax-M3",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5,
            },
            timeout=30,
        )
        assert resp.status_code == 200

    def test_minimax_chat_completion(self, api_key):
        """Test a simple chat completion via MiniMax API."""
        import httpx

        resp = httpx.post(
            "https://api.minimax.io/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "MiniMax-M3",
                "messages": [{"role": "user", "content": "Say hello in one word."}],
                "max_tokens": 10,
            },
            timeout=30,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "choices" in data
        assert len(data["choices"]) > 0

    def test_minimax_m27_highspeed_model(self, api_key):
        """Test that M2.7-highspeed model is also accessible."""
        import httpx

        resp = httpx.post(
            "https://api.minimax.io/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "MiniMax-M2.7-highspeed",
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5,
            },
            timeout=30,
        )
        assert resp.status_code == 200
