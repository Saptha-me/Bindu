"""
Tests for the PostgreSQL storage provider for cognitive agent states.
"""

import os
import uuid
import unittest
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from pebble.db.base import Base
from pebble.db.models import CognitiveState, AgentInteraction
from pebble.db.storage import PostgresStateProvider


class TestPostgresStateProvider(unittest.TestCase):
    """Test suite for the PostgresStateProvider class."""
    
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
        cls.test_state = {
            "episodic_memory": [{"event": "Test event"}],
            "semantic_memory": {"key": "Test knowledge"},
            "working_memory": {"task": "Test task"},
            "context": {"environment": "Test environment"}
        }
    
    def setUp(self):
        """Create a new session and provider for each test."""
        self.session = self.Session()
        
        # Create provider with mocked environment variables
        with patch.dict(os.environ, {
            'POSTGRES_USER': 'test_user',
            'POSTGRES_PASSWORD': 'test_password',
            'POSTGRES_HOST': 'localhost',
            'POSTGRES_PORT': '5432',
            'POSTGRES_DB': 'test_db'
        }):
            self.provider = PostgresStateProvider()
            
            # Inject test session into provider
            self.provider.Session = self.Session
            self.provider.db = self.session
    
    def tearDown(self):
        """Clean up after each test."""
        self.session.query(CognitiveState).delete()
        self.session.query(AgentInteraction).delete()
        self.session.commit()
        self.session.close()
    
    def test_save_and_load_state(self):
        """Test saving and loading a cognitive state."""
        # Save state
        result = self.provider.save_state(
            agent_id=self.agent_id,
            session_id=self.session_id,
            state_data=self.test_state
        )
        
        # Check save result
        assert result is True
        
        # Verify state is in database
        state_record = self.session.query(CognitiveState).filter_by(
            agent_id=self.agent_id,
            session_id=self.session_id
        ).first()
        
        assert state_record is not None
        assert state_record.state_data == self.test_state
        
        # Load state
        loaded_state = self.provider.load_state(
            agent_id=self.agent_id,
            session_id=self.session_id
        )
        
        # Verify loaded state matches original
        assert loaded_state == self.test_state
    
    def test_update_existing_state(self):
        """Test updating an existing cognitive state."""
        # First save
        self.provider.save_state(
            agent_id=self.agent_id,
            session_id=self.session_id,
            state_data=self.test_state
        )
        
        # Modified state
        updated_state = {
            **self.test_state,
            "episodic_memory": [
                {"event": "Test event"},
                {"event": "New event"}
            ]
        }
        
        # Update state
        result = self.provider.save_state(
            agent_id=self.agent_id,
            session_id=self.session_id,
            state_data=updated_state
        )
        
        # Check update result
        assert result is True
        
        # Verify state is updated in database
        state_record = self.session.query(CognitiveState).filter_by(
            agent_id=self.agent_id,
            session_id=self.session_id
        ).first()
        
        assert state_record is not None
        assert state_record.state_data == updated_state
        assert len(state_record.state_data["episodic_memory"]) == 2
    
    def test_load_nonexistent_state(self):
        """Test loading a state that does not exist."""
        # Load with non-existent IDs
        nonexistent_id = str(uuid.uuid4())
        loaded_state = self.provider.load_state(
            agent_id=nonexistent_id,
            session_id=self.session_id
        )
        
        # Should return None
        assert loaded_state is None
    
    def test_log_interaction(self):
        """Test logging an agent interaction."""
        # Log an interaction
        self.provider.log_interaction(
            agent_id=self.agent_id,
            session_id=self.session_id,
            operation="test",
            request_content="Test request",
            response_content="Test response",
            metadata={"test": "metadata"}
        )
        
        # Verify interaction is in database
        interactions = self.session.query(AgentInteraction).filter_by(
            agent_id=self.agent_id,
            session_id=self.session_id
        ).all()
        
        assert len(interactions) == 1
        assert interactions[0].operation == "test"
        assert interactions[0].request_content == "Test request"
        assert interactions[0].response_content == "Test response"
        assert interactions[0].metadata == {"test": "metadata"}
        assert interactions[0].error is None
    
    def test_log_interaction_with_error(self):
        """Test logging an agent interaction with an error."""
        # Log an interaction with error
        self.provider.log_interaction(
            agent_id=self.agent_id,
            session_id=self.session_id,
            operation="test_error",
            request_content="Test request",
            response_content=None,
            metadata={"test": "metadata"},
            error="Test error message"
        )
        
        # Verify interaction is in database
        interactions = self.session.query(AgentInteraction).filter_by(
            agent_id=self.agent_id,
            session_id=self.session_id,
            operation="test_error"
        ).all()
        
        assert len(interactions) == 1
        assert interactions[0].request_content == "Test request"
        assert interactions[0].response_content is None
        assert interactions[0].error == "Test error message"
    
    def test_prune_old_states(self):
        """Test pruning old cognitive states."""
        # Create multiple states with same agent ID but different session IDs
        for i in range(5):
            session_id = f"test-session-{i}"
            self.provider.save_state(
                agent_id=self.agent_id,
                session_id=session_id,
                state_data=self.test_state
            )
        
        # Verify we have 5 states
        states = self.session.query(CognitiveState).filter_by(
            agent_id=self.agent_id
        ).all()
        assert len(states) == 5
        
        # Prune to keep only 2 most recent
        self.provider.prune_old_states(
            agent_id=self.agent_id,
            keep_newest=2
        )
        
        # Verify we now have only 2 states
        states = self.session.query(CognitiveState).filter_by(
            agent_id=self.agent_id
        ).all()
        assert len(states) == 2
        
        # Verify the correct ones were kept (sessions 3 and 4)
        session_ids = [state.session_id for state in states]
        assert "test-session-3" in session_ids
        assert "test-session-4" in session_ids
