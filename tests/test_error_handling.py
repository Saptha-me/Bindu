"""Tests for error handling in pebbling."""

import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from pebbling.server.rest_server import create_rest_server
from pebbling.server.schemas.model import AgentResponse, ErrorResponse, MessageRole


class TestErrorHandling:
    """Tests for error handling in all components."""

    @pytest.fixture
    def protocol_handler(self):
        """Create a mock protocol handler."""
        handler = MagicMock()
        handler.agent = MagicMock()
        handler.agent_id = str(uuid.uuid4())
        return handler

    @pytest.fixture
    def client(self, protocol_handler):
        """Create a client with the test protocol handler."""
        app = create_rest_server(protocol_handler)
        return TestClient(app)

    @pytest.fixture
    def audio_request_json(self):
        """Create a sample audio request."""
        return {
            "input": "Listen to this audio",
            "audio": {
                "id": str(uuid.uuid4()),
                "url": "https://example.com/audio.mp3",
                "length": "10s",
                "mime_type": "audio/mp3",
            },
            "user_id": "test-user",
            "session_id": str(uuid.uuid4()),
        }

    @pytest.fixture
    def image_request_json(self):
        """Create a sample image request."""
        return {
            "input": "What's in this image?",
            "media_type": "image",
            "media": {
                "id": str(uuid.uuid4()),
                "url": "https://example.com/image.jpg",
                "alt_text": "Sample image",
                "width": 800,
                "height": 600,
                "mime_type": "image/jpeg",
            },
            "user_id": "test-user",
            "session_id": str(uuid.uuid4()),
        }

    @patch("pebbling.server.rest_server.ErrorResponse")
    def test_health_check_error(self, mock_error_response, client, protocol_handler):
        """Test error handling in health check."""
        # Setup the mock to return a JSONResponse
        mock_error = ErrorResponse(status_code=500, status="error", message="Health check failed: Agent error")
        mock_error_response.return_value = JSONResponse(status_code=500, content=mock_error.model_dump())

        # Cause the agent status to fail
        protocol_handler.agent.get_status.side_effect = Exception("Agent error")

        # Make the request
        response = client.get("/health")

        # Check the response
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "Health check failed" in data["message"]

    @patch("pebbling.server.rest_server.ErrorResponse")
    def test_act_error(self, mock_error_response, client, protocol_handler):
        """Test error handling in act endpoint."""
        # Setup the mock to return a JSONResponse
        mock_error = ErrorResponse(status_code=500, status="error", message="Agent execution failed: Action error")
        mock_error_response.return_value = JSONResponse(status_code=500, content=mock_error.model_dump())

        # Set up the handler to raise an exception
        protocol_handler.act.side_effect = Exception("Action error")

        # Create request data
        request_data = {"input": "Test message", "user_id": "test-user", "session_id": str(uuid.uuid4())}

        # Make the request
        response = client.post("/act", json=request_data)

        # Check the response
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "Agent execution failed" in data["message"]

    @patch("pebbling.server.rest_server.ErrorResponse")
    def test_listen_error(self, mock_error_response, client, protocol_handler, audio_request_json):
        """Test error handling in listen endpoint."""
        # Setup the mock to return a JSONResponse
        mock_error = ErrorResponse(status_code=500, status="error", message="Audio processing failed: Listen error")
        mock_error_response.return_value = JSONResponse(status_code=500, content=mock_error.model_dump())

        # Set up the handler to raise an exception
        protocol_handler.listen.side_effect = Exception("Listen error")

        # Make the request
        response = client.post("/listen", json=audio_request_json)

        # Check the response
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "Audio processing failed" in data["message"]

    @patch("pebbling.server.rest_server.ErrorResponse")
    def test_view_error(self, mock_error_response, client, protocol_handler, image_request_json):
        """Test error handling in view endpoint."""
        # Setup the mock to return a JSONResponse
        mock_error = ErrorResponse(status_code=500, status="error", message="Media processing failed: View error")
        mock_error_response.return_value = JSONResponse(status_code=500, content=mock_error.model_dump())

        # Set up the handler to raise an exception
        protocol_handler.view.side_effect = Exception("View error")

        # Make the request
        response = client.post("/view", json=image_request_json)

        # Check the response
        assert response.status_code == 500
        data = response.json()
        assert data["status"] == "error"
        assert "Media processing failed" in data["message"]

    def test_error_response_format(self):
        """Test the ErrorResponse model."""
        error = ErrorResponse(status_code=400, status="error", message="Test error message")
        assert error.status_code == 400
        assert error.status == "error"
        assert error.message == "Test error message"

    def test_agent_response_error_status(self):
        """Test agent response with error status."""
        response = AgentResponse(
            agent_id=str(uuid.uuid4()),
            session_id=str(uuid.uuid4()),
            content="Error occurred",
            status="error",
            role=MessageRole.SYSTEM,
            metadata={"error": "Test error"},
        )
        assert response.status == "error"
        assert response.metadata["error"] == "Test error"
