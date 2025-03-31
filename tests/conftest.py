"""Test fixtures for the pebble package."""

import os
import tempfile
import pytest
from pathlib import Path
from typing import Dict, Any

import httpx
from fastapi.testclient import TestClient

from pebble.core.protocol import AgentProtocol, CognitiveAgentProtocol
from pebble.schemas.models import ActionRequest, ActionResponse, MessageRole
from pebble.adapters.base import BaseAdapter

class MockAgent:
    """Mock agent for testing."""
    
    def __init__(self, responses=None):
        """Initialize the mock agent.
        
        Args:
            responses: Dict mapping input strings to output strings
        """
        self.responses = responses or {"Hello": "Hi there!"}
        self.last_inputs = []
        self.has_vision = False
        self.has_audio = False
    
    def run(self, prompt=None, images=None, videos=None, audio=None):
        """Run the agent."""
        self.last_inputs.append({
            "prompt": prompt,
            "images": images,
            "videos": videos,
            "audio": audio
        })
        
        # Check if the exact prompt is in responses
        if prompt in self.responses:
            return self.responses[prompt]
            
        # Fall back to a default response
        return "I don't know how to respond to that."


class MockAdapter(BaseAdapter):
    """Mock adapter for testing."""
    
    def __init__(self, agent_id=None, name=None, metadata=None, cognitive=False):
        """Initialize the mock adapter."""
        super().__init__(agent_id, name, metadata)
        self.last_request = None
        self.mock_responses = {}
        self.cognitive = cognitive
        
        if cognitive:
            self.capabilities = ["act"]
            self.cognitive_state = {
                "perceptual_state": {},
                "mental_state": {}
            }
    
    def register_response(self, content: str, response: str):
        """Register a mock response for a given input."""
        self.mock_responses[content] = response
    
    def act(self, request: ActionRequest) -> ActionResponse:
        """Process an action request."""
        self.last_request = request
        
        # Check if we have a registered response
        if request.content in self.mock_responses:
            response_content = self.mock_responses[request.content]
        else:
            response_content = f"Received: {request.content}"
        
        return ActionResponse(
            content=response_content,
            session_id=request.session_id,
            role=MessageRole.ASSISTANT,
            finished=True,
            metadata={"processed": True}
        )


@pytest.fixture
def mock_agent():
    """Return a mock agent for testing."""
    return MockAgent()


@pytest.fixture
def mock_vision_agent():
    """Return a mock agent with vision capabilities."""
    agent = MockAgent()
    agent.has_vision = True
    return agent


@pytest.fixture
def mock_adapter():
    """Return a mock adapter for testing."""
    return MockAdapter(name="MockAdapter")


@pytest.fixture
def mock_cognitive_adapter():
    """Return a mock cognitive adapter for testing."""
    return MockAdapter(name="MockCognitiveAdapter", cognitive=True)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def test_image_path(temp_dir):
    """Create a test image file and return its path."""
    image_path = temp_dir / "test_image.jpg"
    
    # Create a small test image file
    with open(image_path, "wb") as f:
        f.write(b"MOCK_IMAGE_DATA")
    
    return image_path


@pytest.fixture
def test_video_path(temp_dir):
    """Create a test video file and return its path."""
    video_path = temp_dir / "test_video.mp4"
    
    # Create a small test video file
    with open(video_path, "wb") as f:
        f.write(b"MOCK_VIDEO_DATA")
    
    return video_path


@pytest.fixture
def mock_httpx_client(monkeypatch):
    """Mock httpx client for testing URL downloads."""
    class MockResponse:
        def __init__(self, content, status_code=200):
            self.content = content
            self.status_code = status_code
        
        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError("Error", request=None, response=self)
    
    class MockClient:
        def __init__(self):
            self.responses = {}
            
        def register_response(self, url, content, status_code=200):
            self.responses[url] = MockResponse(content, status_code)
            
        def get(self, url, **kwargs):
            if url in self.responses:
                return self.responses[url]
            return MockResponse(b"DEFAULT_RESPONSE", 200)
    
    mock_client = MockClient()
    
    def mock_get(url, **kwargs):
        return mock_client.get(url, **kwargs)
    
    monkeypatch.setattr(httpx, "get", mock_get)
    
    return mock_client