# 
# |---------------------------------------------------------|
# |                                                         |
# |                 Give Feedback / Get Help                |
# | https://github.com/Pebbling-ai/pebble/issues/new/choose |
# |                                                         |
# |---------------------------------------------------------|
#
#  Thank you users! We ❤️ you! - 🐧

"""
Session store for managing per-session agent contexts.

Handles session-scoped agent contexts, conversation history, and state management.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from dataclasses import dataclass, field

from pebbling.protocol.types import Message, Task
from .memory_store import MemoryStore


@dataclass
class AgentContext:
    """Context for a specific agent within a session."""
    agent_id: str
    session_id: str
    conversation_history: List[Message] = field(default_factory=list)
    task_history: List[str] = field(default_factory=list)  # Task IDs
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: str(UUID(int=0)))  # Placeholder for timestamp


@dataclass
class Session:
    """Session containing multiple agent contexts."""
    id: str
    agent_contexts: Dict[str, AgentContext] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: str(UUID(int=0)))  # Placeholder for timestamp


class SessionStore(MemoryStore[Session]):
    """Store for managing sessions and per-session agent contexts."""
    
    async def create_session(self, session_id: Optional[str] = None) -> Session:
        """Create a new session."""
        if session_id is None:
            session_id = str(uuid4())
        
        session = Session(id=session_id)
        await self.set(session_id, session)
        return session
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID."""
        return await self.get(session_id)
    
    async def get_or_create_session(self, session_id: str) -> Session:
        """Get an existing session or create a new one."""
        session = await self.get_session(session_id)
        if session is None:
            session = await self.create_session(session_id)
        return session
    
    async def get_agent_context(self, session_id: str, agent_id: str) -> Optional[AgentContext]:
        """Get agent context within a session."""
        session = await self.get_session(session_id)
        if session is None:
            return None
        return session.agent_contexts.get(agent_id)
    
    async def create_agent_context(self, session_id: str, agent_id: str) -> AgentContext:
        """Create a new agent context within a session."""
        session = await self.get_or_create_session(session_id)
        
        context = AgentContext(agent_id=agent_id, session_id=session_id)
        session.agent_contexts[agent_id] = context
        
        await self.set(session_id, session)
        return context
    
    async def get_or_create_agent_context(self, session_id: str, agent_id: str) -> AgentContext:
        """Get existing agent context or create a new one."""
        context = await self.get_agent_context(session_id, agent_id)
        if context is None:
            context = await self.create_agent_context(session_id, agent_id)
        return context
    
    async def add_message_to_context(self, session_id: str, agent_id: str, message: Message) -> bool:
        """Add a message to agent's conversation history."""
        context = await self.get_agent_context(session_id, agent_id)
        if context is None:
            return False
        
        context.conversation_history.append(message)
        
        # Update the session
        session = await self.get_session(session_id)
        if session:
            session.agent_contexts[agent_id] = context
            await self.set(session_id, session)
            return True
        return False
    
    async def add_task_to_context(self, session_id: str, agent_id: str, task_id: str) -> bool:
        """Add a task ID to agent's task history."""
        context = await self.get_agent_context(session_id, agent_id)
        if context is None:
            return False
        
        context.task_history.append(task_id)
        
        # Update the session
        session = await self.get_session(session_id)
        if session:
            session.agent_contexts[agent_id] = context
            await self.set(session_id, session)
            return True
        return False
    
    async def update_context_metadata(self, session_id: str, agent_id: str, metadata: Dict[str, Any]) -> bool:
        """Update agent context metadata."""
        context = await self.get_agent_context(session_id, agent_id)
        if context is None:
            return False
        
        context.metadata.update(metadata)
        
        # Update the session
        session = await self.get_session(session_id)
        if session:
            session.agent_contexts[agent_id] = context
            await self.set(session_id, session)
            return True
        return False
