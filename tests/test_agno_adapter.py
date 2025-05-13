"""
Tests for the Agno adapter.
"""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from agno.agent import Agent as AgnoAgent

from pebbling.agent.agno_adapter import AgnoProtocolHandler


class TestAgnoAdapter:
    """Tests for the AgnoProtocolHandler."""

    @pytest.fixture
    def agno_agent(self):
        """Create a mock Agno agent."""
        agent = MagicMock(spec=AgnoAgent)
        agent.context = {}
        return agent

    @pytest.fixture
    def protocol_handler(self, agno_agent):
        """Create an AgnoProtocolHandler with a mock agent."""
        # Use a valid UUID string format for agent_id
        return AgnoProtocolHandler(agent=agno_agent, agent_id=str(uuid.uuid4()))

    @pytest.mark.asyncio
    async def test_handle_context_add(self, protocol_handler):
        """Test adding context."""
        params = {
            "operation": "add",
            "key": "test_key",
            "value": "test_value",
            "id": "test-id",
        }

        result = await protocol_handler.handle_Context(params)

        # Check that we have a valid result
        assert "result" in result
        assert result["result"]["status"] == "success"
        assert result["result"]["key"] == "test_key"
        assert result["result"]["message"] == "Context added successfully"
        assert protocol_handler.agent.context["test_key"] == "test_value"

    @pytest.mark.asyncio
    async def test_handle_context_missing_key(self, protocol_handler):
        """Test adding context with missing key."""
        params = {"operation": "add", "value": "test_value", "id": "test-id"}

        result = await protocol_handler.handle_Context(params)

        assert "error" in result
        assert result["error"]["code"] == 400

    @pytest.mark.asyncio
    async def test_handle_context_update(self, protocol_handler):
        """Test updating context."""
        # First add the context with the correct structure (dict with value and metadata)
        protocol_handler.agent.context["test_key"] = {
            "value": "old_value",
            "metadata": {},
        }

        params = {
            "operation": "update",
            "key": "test_key",
            "value": "new_value",
            "id": "test-id",
        }

        result = await protocol_handler.handle_Context(params)

        # Check that we have a valid result
        assert "result" in result
        assert result["result"]["status"] == "success"
        assert result["result"]["key"] == "test_key"
        assert result["result"]["message"] == "Context updated successfully"

        # After update, the context value is a simple string, not a dictionary
        assert protocol_handler.agent.context["test_key"] == "new_value"

    @pytest.mark.asyncio
    async def test_handle_context_delete(self, protocol_handler):
        """Test deleting context."""
        # First add the context with the correct structure
        protocol_handler.agent.context["test_key"] = {
            "value": "test_value",
            "metadata": {},
        }

        params = {"operation": "delete", "key": "test_key", "id": "test-id"}

        result = await protocol_handler.handle_Context(params)

        # Check that we have a valid result
        assert "result" in result
        assert result["result"]["status"] == "success"
        assert result["result"]["key"] == "test_key"
        assert result["result"]["message"] == "Context deleted successfully"
        assert "test_key" not in protocol_handler.agent.context

    @pytest.fixture
    def mock_audio(self):
        """Create a mock audio object with URL and base64 variants."""
        from pebbling.server.schemas.model import AudioArtifact

        # Create an actual AudioArtifact instance with valid UUID
        return AudioArtifact(id=uuid.uuid4(), url="http://example.com/audio.mp3", base64_audio=None)

    @pytest.fixture
    def mock_base64_audio(self):
        """Create a mock audio object with base64 content."""
        from pebbling.server.schemas.model import AudioArtifact

        # Create an actual AudioArtifact instance with valid UUID and base64 content
        return AudioArtifact(
            id=uuid.uuid4(),
            url=None,
            # This is a valid base64 string for testing
            base64_audio="YXVkaW9jb250ZW50",
        )

    @pytest.fixture
    def mock_image(self):
        """Create a mock image object with base64 variant to avoid HTTP requests."""
        from pebbling.server.schemas.model import ImageArtifact

        # Use base64 encoded image instead of URL to avoid HTTP requests
        return ImageArtifact(
            id=uuid.uuid4(),
            url=None,
            # Simple base64 encoded image data
            base64_image="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==",
        )

    @pytest.mark.asyncio
    async def test_listen_with_url_audio(self, protocol_handler, mock_audio):
        """Test audio processing with URL-based audio."""
        # Configure the mock agent to return a response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "content": "Audio processed successfully",
            "messages": [{"role": "assistant", "content": "Audio processed successfully"}],
            "metrics": {"tokens": 10},
        }
        protocol_handler.agent.run.return_value = mock_response

        # Mock the requests module for URL downloading
        with patch("pebbling.agent.agno_adapter.requests.get") as mock_get:
            # Set up the mock response for requests.get
            mock_get_response = MagicMock()
            mock_get_response.content = b"audio content"
            mock_get.return_value = mock_get_response

            # Call the listen method - Not awaiting as it's not async
            response = protocol_handler.listen(
                message="Test message", audio=mock_audio, user_id="test-user", session_id=str(uuid.uuid4())
            )

            # Verify response
            assert response.content == "Audio processed successfully"
            protocol_handler.agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_listen_with_base64_audio(self, protocol_handler, mock_base64_audio):
        """Test audio processing with base64 audio content."""
        # Configure the mock agent to return a response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "content": "Base64 audio processed",
            "messages": [{"role": "assistant", "content": "Base64 audio processed"}],
            "metrics": {"tokens": 8},
        }
        protocol_handler.agent.run.return_value = mock_response

        # Patch the _decode_base64 method
        with patch.object(protocol_handler, "_decode_base64", return_value=b"decoded audio") as mock_decode:
            # Call the listen method - Not awaiting as it's not async
            response = protocol_handler.listen(
                message="Process this audio", audio=mock_base64_audio, user_id="test-user", session_id=str(uuid.uuid4())
            )

            # Verify response
            assert response.content == "Base64 audio processed"
            assert mock_decode.called
            protocol_handler.agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_view_with_image(self, protocol_handler, mock_image):
        """Test image processing via the view method."""
        # Configure the mock agent to return a response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "content": "Image analysis result",
            "messages": [{"role": "assistant", "content": "Image analysis result"}],
            "metrics": {"tokens": 12},
        }
        protocol_handler.agent.run.return_value = mock_response

        # We can also patch the base64 decoder to make sure it works
        with patch.object(protocol_handler, "_decode_base64", return_value=b"decoded image data"):
            # Call the view method - Not awaiting as it's not async
            response = protocol_handler.view(
                message="Analyze this image", media=mock_image, user_id="test-user", session_id=str(uuid.uuid4())
            )

            # Verify response
            assert response.content == "Image analysis result"
            protocol_handler.agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_listen_error_handling(self, protocol_handler, mock_audio):
        """Test error handling in listen method."""
        # For error handling tests, we need to examine what actually happens in the code
        # The error should be logged but the response will have a success status
        # with error information in the content

        # Mock the requests module for URL downloading
        with patch("pebbling.agent.agno_adapter.requests.get") as mock_get:
            # Simulate HTTP error by having requests.get raise an exception
            mock_get.side_effect = Exception("Network error")

            # Call the listen method - Not awaiting as it's not async
            response = protocol_handler.listen(
                message="Test message", audio=mock_audio, user_id="test-user", session_id=str(uuid.uuid4())
            )

            # Verify response contains error information
            assert "Network error" in response.content

    @pytest.mark.asyncio
    async def test_act_basic_functionality(self, protocol_handler):
        """Test basic functionality of the act method."""
        # Configure the mock agent to return a response
        mock_response = MagicMock()
        mock_response.to_dict.return_value = {
            "content": "Text processed successfully",
            "messages": [{"role": "assistant", "content": "Text processed successfully"}],
            "metrics": {"tokens": 6},
        }
        protocol_handler.agent.run.return_value = mock_response

        # Call the act method - Not awaiting as it's not async
        response = protocol_handler.act(message="Process this text", user_id="test-user", session_id=str(uuid.uuid4()))

        # Verify response
        assert response.content == "Text processed successfully"
        protocol_handler.agent.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_errors(self, protocol_handler):
        """Test error handling mechanism in AgnoProtocolHandler."""
        # Set up the agent to raise an exception when run is called
        protocol_handler.agent.run.side_effect = RuntimeError("Agent runtime error")

        # Call the act method - Not awaiting as it's not async
        response = protocol_handler.act(
            message="This will cause an error", user_id="test-user", session_id=str(uuid.uuid4())
        )

        # Verify that error information is in the content
        # In actual implementation, status might not change to "error"
        assert "Agent runtime error" in response.content
