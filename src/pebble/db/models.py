"""
SQLAlchemy models for Pebble framework database.
"""

import uuid
import json
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB

from pebble.db.base import Base


class CognitiveState(Base):
    """Model for storing cognitive agent states."""
    
    __tablename__ = "cognitive_states"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    state_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Create a compound index for efficient lookups
    __table_args__ = (
        Index('ix_cognitive_states_agent_session', 'agent_id', 'session_id'),
    )
    
    @classmethod
    def create_or_update(cls, db, agent_id: str, session_id: str, state_data: Dict[str, Any]) -> "CognitiveState":
        """Create or update a cognitive state record.
        
        Args:
            db: Database session
            agent_id: ID of the agent
            session_id: ID of the session
            state_data: Cognitive state data as a dictionary
            
        Returns:
            CognitiveState: The created or updated cognitive state record
        """
        # Check if a record already exists
        record = db.query(cls).filter(
            cls.agent_id == agent_id,
            cls.session_id == session_id
        ).first()
        
        if record:
            # Update existing record
            record.state_data = state_data
            record.updated_at = datetime.utcnow()
        else:
            # Create new record
            record = cls(
                agent_id=agent_id,
                session_id=session_id,
                state_data=state_data
            )
            db.add(record)
        
        db.commit()
        db.refresh(record)
        return record
    
    @classmethod
    def get_state(cls, db, agent_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get cognitive state data for an agent and session.
        
        Args:
            db: Database session
            agent_id: ID of the agent
            session_id: ID of the session
            
        Returns:
            Optional[Dict[str, Any]]: Cognitive state data if found, None otherwise
        """
        record = db.query(cls).filter(
            cls.agent_id == agent_id,
            cls.session_id == session_id
        ).first()
        
        if record:
            return record.state_data
        return None
    
    @classmethod
    def prune_old_states(cls, db, days_to_keep: int = 30) -> int:
        """Delete cognitive states older than the specified number of days.
        
        Args:
            db: Database session
            days_to_keep: Number of days to keep states for
            
        Returns:
            int: Number of deleted records
        """
        cutoff_date = datetime.utcnow() - datetime.timedelta(days=days_to_keep)
        result = db.query(cls).filter(cls.updated_at < cutoff_date).delete()
        db.commit()
        return result


class AgentInteraction(Base):
    """Model for logging agent interactions and metrics."""
    
    __tablename__ = "agent_interactions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(String(255), nullable=False, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    operation = Column(String(50), nullable=False, index=True)  # act, listen, see, think
    request_content = Column(Text, nullable=True)
    response_content = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    duration_ms = Column(String(50), nullable=True)  # Duration in milliseconds
    error = Column(Text, nullable=True)  # Error message if any
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    @classmethod
    def log_interaction(
        cls, 
        db, 
        agent_id: str, 
        session_id: str, 
        operation: str,
        request_content: Optional[str] = None,
        response_content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None,
        error: Optional[str] = None
    ) -> "AgentInteraction":
        """Log an agent interaction.
        
        Args:
            db: Database session
            agent_id: ID of the agent
            session_id: ID of the session
            operation: Type of operation (act, listen, see, think)
            request_content: Content of the request
            response_content: Content of the response
            metadata: Additional metadata
            duration_ms: Duration of the operation in milliseconds
            error: Error message if any
            
        Returns:
            AgentInteraction: The created interaction record
        """
        interaction = cls(
            agent_id=agent_id,
            session_id=session_id,
            operation=operation,
            request_content=request_content,
            response_content=response_content,
            metadata_json=metadata,  # Using renamed column
            duration_ms=duration_ms,
            error=error
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        return interaction
