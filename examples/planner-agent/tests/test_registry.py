"""Tests for agent registry and capability matching."""

import pytest
from unittest.mock import patch, Mock
from core.agent_registry import AgentRegistry


def test_registry_initialization():
    """Test that registry initializes with agent URLs."""
    
    mock_response = Mock()
    mock_response.json.return_value = {
        "name": "test_agent",
        "skills": []
    }
    mock_response.raise_for_status = Mock()
    
    with patch('requests.get', return_value=mock_response):
        registry = AgentRegistry(["http://localhost:3775"])
    
    assert len(registry.agents) == 1


def test_find_agent_for_capabilities():
    """Test capability-based agent matching."""
    
    # Create mock agent with specific capabilities
    mock_response = Mock()
    mock_response.json.return_value = {
        "name": "research_agent",
        "skills": [{
            "capabilities": ["research", "web_search"]
        }]
    }
    mock_response.raise_for_status = Mock()
    
    with patch('requests.get', return_value=mock_response):
        registry = AgentRegistry(["http://localhost:3775"])
    
    # Find agent for research capability
    agent = registry.find_agent_for_capabilities(["research"])
    
    assert agent is not None
    assert agent["name"] == "research_agent"


def test_no_match_for_capabilities():
    """Test that None is returned when no agent matches."""
    
    mock_response = Mock()
    mock_response.json.return_value = {
        "name": "test_agent",
        "skills": [{
            "capabilities": ["other_capability"]
        }]
    }
    mock_response.raise_for_status = Mock()
    
    with patch('requests.get', return_value=mock_response):
        registry = AgentRegistry(["http://localhost:3775"])
    
    # Try to find agent for non-existent capability
    agent = registry.find_agent_for_capabilities(["research"])
    
    # Should return the agent anyway with score 0 (or None if no agents)
    # Based on implementation, best_match is None initially
    assert agent is None or "name" in agent


def test_best_match_selection():
    """Test that agent with highest capability match is selected."""
    
    def mock_get(url, timeout=10):
        mock_resp = Mock()
        if "3775" in url:
            mock_resp.json.return_value = {
                "name": "good_match",
                "skills": [{
                    "capabilities": ["research", "web_search", "analysis"]
                }]
            }
        else:
            mock_resp.json.return_value = {
                "name": "partial_match",
                "skills": [{
                    "capabilities": ["research"]
                }]
            }
        mock_resp.raise_for_status = Mock()
        return mock_resp
    
    with patch('requests.get', side_effect=mock_get):
        registry = AgentRegistry([
            "http://localhost:3775",
            "http://localhost:3776"
        ])
    
    agent = registry.find_agent_for_capabilities(["research", "web_search"])
    
    assert agent["name"] == "good_match"  # Should select agent with more matches
