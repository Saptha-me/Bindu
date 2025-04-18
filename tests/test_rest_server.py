"""
Tests for the REST API server.
"""
import json
import pytest
from fastapi.testclient import TestClient

from pebble.server.rest_server import create_rest_server


class TestRestServer:
    """Tests for the REST API server."""
    
    @pytest.fixture
    def client(self, mock_protocol_handler):
        """Create a test client for the REST API server."""
        app = create_rest_server(mock_protocol_handler)
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test the health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["message"] == "Service is running"
        assert "timestamp" in data
    
    def test_run_agent(self, client, sample_request_json):
        """Test the run endpoint."""
        response = client.post("/run", json=sample_request_json)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["content"] == "Test response"
        assert len(data["messages"]) == 1
        assert data["metrics"]["tokens"] == 10
    
    def test_run_agent_empty_input(self, client):
        """Test the run endpoint with empty input."""
        response = client.post("/run", json={"input": ""})
        assert response.status_code == 400
        data = response.json()
        assert data["status"] == "error"
        assert "Input text is required" in data["message"]
    
    def test_run_agent_missing_input(self, client):
        """Test the run endpoint with missing input."""
        response = client.post("/run", json={})
        assert response.status_code == 422  # FastAPI validation error