"""
Storage providers for persistent agent state.
"""

import time
import logging
from typing import Dict, Any, Optional

from sqlalchemy.orm import Session
from pebble.db.models import CognitiveState, AgentInteraction

logger = logging.getLogger(__name__)


class PostgresStateProvider:
    """PostgreSQL storage provider for cognitive agent states."""
    
    def __init__(self, db_session: Session):
        """Initialize with a database session.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
    
    def save_state(self, agent_id: str, session_id: str, state_data: Dict[str, Any]) -> bool:
        """Save cognitive state to the database.
        
        Args:
            agent_id: ID of the agent
            session_id: ID of the session
            state_data: Cognitive state data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            CognitiveState.create_or_update(
                self.db, 
                agent_id=agent_id, 
                session_id=session_id, 
                state_data=state_data
            )
            return True
        except Exception as e:
            logger.error(f"Failed to save cognitive state: {e}")
            return False
    
    def load_state(self, agent_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Load cognitive state from the database.
        
        Args:
            agent_id: ID of the agent
            session_id: ID of the session
            
        Returns:
            Optional[Dict[str, Any]]: Cognitive state data if found, None otherwise
        """
        try:
            return CognitiveState.get_state(self.db, agent_id, session_id)
        except Exception as e:
            logger.error(f"Failed to load cognitive state: {e}")
            return None
    
    def log_interaction(
        self, 
        agent_id: str, 
        session_id: str, 
        operation: str,
        request_content: Optional[str] = None,
        response_content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> bool:
        """Log an agent interaction with timing information.
        
        Args:
            agent_id: ID of the agent
            session_id: ID of the session
            operation: Type of operation (act, listen, see, think)
            request_content: Content of the request
            response_content: Content of the response
            metadata: Additional metadata
            error: Error message if any
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Add timing information
            start_time = metadata.get("start_time") if metadata else None
            
            if start_time:
                # Calculate duration if start_time was provided
                duration_ms = str(int((time.time() - start_time) * 1000))
            else:
                duration_ms = None
                
            # Remove start_time from metadata to avoid storing unnecessary data
            if metadata and "start_time" in metadata:
                metadata = {k: v for k, v in metadata.items() if k != "start_time"}
                
            AgentInteraction.log_interaction(
                self.db,
                agent_id=agent_id,
                session_id=session_id,
                operation=operation,
                request_content=request_content,
                response_content=response_content,
                metadata=metadata,  # Will be mapped to metadata_json in the model
                duration_ms=duration_ms,
                error=error
            )
            return True
        except Exception as e:
            logger.error(f"Failed to log interaction: {e}")
            return False
            
    def prune_old_states(self, days_to_keep: int = 30) -> int:
        """Delete cognitive states older than the specified number of days.
        
        Args:
            days_to_keep: Number of days to keep states for
            
        Returns:
            int: Number of deleted records
        """
        try:
            return CognitiveState.prune_old_states(self.db, days_to_keep)
        except Exception as e:
            logger.error(f"Failed to prune old states: {e}")
            return 0
