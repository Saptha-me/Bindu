"""Tests for executor module (agent-to-agent communication)."""

import pytest
from unittest.mock import patch, Mock
from core.executor import execute_on_agent


def test_execute_on_agent_success():
    """Test successful agent execution with valid JSON-RPC response."""
    
    # Mock HTTP response
    mock_response = Mock()
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "result": {
            "messages": [
                {"role": "user", "content": "Summarize AI trends"},
                {"role": "assistant", "content": "Here are 3 key AI trends..."}
            ]
        },
        "id": 1
    }
    mock_response.raise_for_status = Mock()
    
    with patch('requests.post', return_value=mock_response):
        result = execute_on_agent(
            "http://localhost:3775",
            "Summarize AI trends"
        )
    
    assert result["success"] is True
    assert "trends" in result["content"]
    assert result["agent_url"] == "http://localhost:3775"


def test_execute_on_agent_connection_error():
    """Test agent execution with connection failure."""
    
    with patch('requests.post', side_effect=ConnectionError("Connection refused")):
        result = execute_on_agent(
            "http://localhost:9999",
            "Test task"
        )
    
    assert result["success"] is False
    assert "error" in result  # Just check error field exists


def test_execute_on_agent_timeout():
    """Test agent execution with timeout."""
    
    with patch('requests.post', side_effect=TimeoutError("Timeout")):
        result = execute_on_agent(
            "http://localhost:3775",
            "Test task"
        )
    
    assert result["success"] is False
    assert "error" in result


def test_execute_on_agent_invalid_response():
    """Test agent execution with malformed response."""
    
    mock_response = Mock()
    mock_response.json.return_value = {
        "jsonrpc": "2.0",
        "result": {}  # Missing 'messages' field
    }
    mock_response.raise_for_status = Mock()
    
    with patch('requests.post', return_value=mock_response):
        result = execute_on_agent(
            "http://localhost:3775",
            "Test task"
        )
    
    assert result["success"] is False
    assert "Invalid response format" in result["error"]
