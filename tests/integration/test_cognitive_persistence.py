"""
Integration test for cognitive protocol with PostgreSQL state persistence.

This test demonstrates the full workflow of using a cognitive agent with
PostgreSQL state persistence, including state saving, loading, and interaction logging.
"""

import os
import uuid
import unittest
from unittest.mock import patch, MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pebble.core.cognitive_protocol import CognitiveAgentProtocol
from pebble.core.protocol import AgentProtocol
from pebble.db.base import Base
from pebble.db.models import CognitiveState, AgentInteraction
from pebble.db.storage import PostgresStateProvider
from pebble.schemas.models import CognitiveRequest, StimulusType


class MockAgent(AgentProtocol):
    """Mock agent for testing."""
    
    def __init__(self, agent_id=None):
        """Initialize the mock agent."""
        super().__init__(agent_id or str(uuid.uuid4()))
    
    def process_action(self, request):
        """Mock process_action that returns a predefined response."""
        # Simple mock implementation that echoes the request
        from pebble.schemas.models import ActionResponse
        return ActionResponse(
            agent_id=self.agent_id,
            session_id=request.session_id,
            message=f"Processed: {request.message}",
            metadata=request.metadata
        )


class TestCognitiveProtocolPersistence(unittest.TestCase):
    """Test suite for the CognitiveAgentProtocol with database persistence."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test database."""
        # Use SQLite in-memory database for testing
        cls.engine = create_engine('sqlite:///:memory:')
        cls.Session = sessionmaker(bind=cls.engine)
        
        # Create all tables
        Base.metadata.create_all(cls.engine)
        
        # Test data
        cls.agent_id = str(uuid.uuid4())
        cls.session_id = str(uuid.uuid4())
        
    def setUp(self):
        """Set up each test."""
        self.session = self.Session()
        
        # Create provider with mocked environment variables
        with patch.dict(os.environ, {
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_password',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test_db'
        }):
            self.storage_provider = PostgresStateProvider()
            
            # Inject test session into provider
            self.storage_provider.Session = self.Session
            self.storage_provider.db = self.session
            
            # Create mock base agent
            self.mock_agent = MockAgent(self.agent_id)
            
            # Create cognitive agent with mock base agent
            self.cognitive_agent = CognitiveAgentProtocol(self.mock_agent)
    
    def tearDown(self):
        """Clean up after each test."""
        self.session.query(CognitiveState).delete()
        self.session.query(AgentInteraction).delete()
        self.session.commit()
        self.session.close()
    
    def test_cognitive_act_with_persistence(self):
        """Test acting with state persistence."""
        # First interaction
        response1 = self.cognitive_agent.act(CognitiveRequest(
            agent_id=self.agent_id,
            session_id=self.session_id,
            content="Tell me about yourself",
            stimulus_type=StimulusType.ACTION,
            metadata={"storage_provider": self.storage_provider}
        ))
        
        # Verify response
        assert response1.content.startswith("Processed:")
        
        # Verify state was saved
        state_record = self.session.query(CognitiveState).filter_by(
            agent_id=self.agent_id,
            session_id=self.session_id
        ).first()
        
        assert state_record is not None
        assert "episodic_memory" in state_record.state_data
        
        # Verify interaction was logged
        interaction = self.session.query(AgentInteraction).filter_by(
            agent_id=self.agent_id,
            session_id=self.session_id
        ).first()
        
        assert interaction is not None
        assert interaction.operation == "act"
        assert interaction.request_content == "Tell me about yourself"
        assert interaction.response_content.startswith("Processed:")
        
        # Create a new cognitive agent (simulating a new instance)
        new_mock_agent = MockAgent(self.agent_id)
        new_cognitive_agent = CognitiveAgentProtocol(new_mock_agent)
        
        # Second interaction with new agent instance (should load previous state)
        response2 = new_cognitive_agent.act(CognitiveRequest(
            agent_id=self.agent_id,
            session_id=self.session_id,
            content="What did I ask you before?",
            stimulus_type=StimulusType.ACTION,
            metadata={"storage_provider": self.storage_provider}
        ))
        
        # Verify response
        assert response2.content.startswith("Processed:")
        
        # Verify we now have two interactions
        interactions = self.session.query(AgentInteraction).filter_by(
            agent_id=self.agent_id,
            session_id=self.session_id
        ).all()
        
        assert len(interactions) == 2
    
    def test_error_handling_and_retry(self):
        """Test error handling and retry logic with persistence."""
        # Create a mock agent that raises an exception on first call but succeeds on retry
        failing_mock_agent = MockAgent(self.agent_id)
        
        # Make the first process_action call raise an exception
        original_process_action = failing_mock_agent.process_action
        call_count = [0]  # Use a list to make it mutable inside the closure
        
        def mock_process_action(request):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Test error")
            return original_process_action(request)
        
        failing_mock_agent.process_action = mock_process_action
        
        # Create cognitive agent with failing mock agent
        failing_cognitive_agent = CognitiveAgentProtocol(failing_mock_agent)
        
        # Call the agent (should fail first, then retry successfully)
        response = failing_cognitive_agent.act(CognitiveRequest(
            agent_id=self.agent_id,
            session_id=self.session_id,
            content="Process this with retry",
            stimulus_type=StimulusType.ACTION,
            metadata={"storage_provider": self.storage_provider}
        ))
        
        # Verify response indicates success (from retry)
        assert response.content.startswith("Processed:") 
        
        # Verify interaction was logged with eventual success
        interactions = self.session.query(AgentInteraction).filter_by(
            agent_id=self.agent_id,
            session_id=self.session_id
        ).all()
        
        assert len(interactions) == 1
        assert interactions[0].operation == "act"
        assert interactions[0].error is None  # Should be null since retry succeeded
    
    def test_memory_pruning(self):
        """Test memory pruning works with persistence."""
        # Create agent with large episodic memory
        self.cognitive_agent.cognitive_state["episodic_memory"] = [
            {"event": f"Event {i}"} for i in range(150)  # More than our 100 threshold
        ]
        
        # Perform action that will trigger pruning
        response = self.cognitive_agent.act(CognitiveRequest(
            agent_id=self.agent_id,
            session_id=self.session_id,
            content="Test pruning",
            stimulus_type=StimulusType.ACTION,
            metadata={"storage_provider": self.storage_provider}
        ))
        
        # Verify episodic memory was pruned
        assert len(self.cognitive_agent.cognitive_state["episodic_memory"]) == 100
        
        # Verify pruned state was saved to DB
        state_record = self.session.query(CognitiveState).filter_by(
            agent_id=self.agent_id,
            session_id=self.session_id
        ).first()
        
        assert state_record is not None
        assert len(state_record.state_data["episodic_memory"]) == 100
        
        # Verify oldest events (first 10) were kept
        for i in range(10):
            assert state_record.state_data["episodic_memory"][i]["event"] == f"Event {i}"


if __name__ == "__main__":
    unittest.main()
