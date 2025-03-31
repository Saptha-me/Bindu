"""
Agent registry for managing multiple agents and their communication.

This module provides a standardized registry system for agent-to-agent communication.
"""
from typing import Dict, Any, List, Optional
import time
import uuid
import logging

from pebble.core.protocol import CognitiveAgentProtocol
from pebble.schemas.models import ActionRequest, ActionResponse, MessageRole

logger = logging.getLogger("pebble.registry")

class AgentRegistry:
    """Registry for tracking all agents in the system to enable inter-agent communication."""
    
    def __init__(self):
        """Initialize the agent registry."""
        self.agents = {}  # name -> agent (protocol adapter)
        self.communication_style = "simplified"  # or "full" for more detailed exchanges
        self.communication_display = True  # for logging/display purposes
        self.relationships = {}  # stores relationship information between agents
        self.handoff_history = {}  # tracks handoffs between agents
        self.conversation_context = {}  # stores ongoing conversation context

        # mTLS configuration
        self.use_mtls = use_mtls
        self.certs_dir = certs_dir
        self.secure_clients = {}  # agent_name -> SecureAgentClient
    
    def register(self, name: str, adapter: CognitiveAgentProtocol, roles=None, capabilities=None) -> None:
        """Register an agent in the registry with roles and capabilities.
        
        Args:
            name: The name of the agent
            adapter: The protocol adapter for the agent
            roles: List of roles the agent can fulfill (e.g., "math_expert", "customer_support")
            capabilities: Specific capabilities this agent has (will be merged with detected capabilities)
        """
        # Default values
        if roles is None:
            roles = []
        
        if capabilities is None:
            capabilities = []
            
        # Merge capabilities with what's in the adapter
        if hasattr(adapter, 'capabilities'):
            capabilities = list(set(capabilities + adapter.capabilities))
            
        # Store agent with its roles and capabilities    
        self.agents[name] = {
            "adapter": adapter,
            "roles": roles,
            "capabilities": capabilities,
            "trust_level": 0.5,  # Default trust level (0.0 to 1.0)
            "specialization": {},  # Will store domain-specific expertise scores
        }
        
        # Initialize relationship tracking for this agent
        self.relationships[name] = {}
        
        # Initialize handoff history for this agent
        self.handoff_history[name] = []
        
        # Update the agent's cognitive state with access to other agents
        if hasattr(adapter, 'cognitive_state'):
            # Add the registry to the agent's metadata for easy access
            adapter.metadata["agent_registry"] = self
            
            # Update accessible agents in cognitive state with relationship information
            accessible_agents = []
            for other_name, other_data in self.agents.items():
                if other_name != name:
                    # Define relationship type based on role overlap
                    relationship_type = self._determine_relationship_type(name, other_name)
                    
                    # Create agent reference with relationship info
                    agent_reference = {
                        "name": other_name,
                        "agent_id": str(other_data["adapter"].agent_id),
                        "relation": relationship_type,
                        "roles": other_data["roles"],
                        "capabilities": other_data["capabilities"],
                        "trust_level": 0.5  # Default initial trust
                    }
                    accessible_agents.append(agent_reference)
                    
                    # Initialize relationship between these agents
                    self.relationships[name][other_name] = {
                        "type": relationship_type,
                        "trust_level": 0.5,
                        "interaction_count": 0,
                        "last_interaction": None
                    }
            
            # Add to mental state in cognitive state
            if "mental_state" not in adapter.cognitive_state:
                adapter.cognitive_state["mental_state"] = {}
            
            adapter.cognitive_state["mental_state"]["accessible_agents"] = accessible_agents

            # Generate certificates for mTLS if enabled
        if self.use_mtls:
            agent_id = str(adapter.agent_id)
            try:
                # Generate certificate and key if they don't exist
                cert_path, key_path = generate_agent_certificate(agent_id, self.certs_dir)
                
                # Store paths in agent metadata
                adapter.metadata["cert_path"] = str(cert_path)
                adapter.metadata["key_path"] = str(key_path)
                
                # Create secure client for this agent
                self.secure_clients[name] = SecureAgentClient(
                    agent_id=agent_id,
                    cert_path=cert_path,
                    key_path=key_path
                )
                logger.info(f"mTLS enabled for agent {name}")
            except Exception as e:
                logger.error(f"Failed to setup mTLS for agent {name}: {str(e)}")
    
    def _determine_relationship_type(self, agent1: str, agent2: str) -> str:
        """Determine the relationship type between two agents based on roles.
        
        Args:
            agent1: The first agent name
            agent2: The second agent name
            
        Returns:
            The relationship type as a string
        """
        # If either agent doesn't exist yet, return default
        if agent1 not in self.agents or agent2 not in self.agents:
            return "Colleague agent"
            
        # Get roles for both agents
        agent1_roles = self.agents[agent1]["roles"]
        agent2_roles = self.agents[agent2]["roles"]
        
        # Check for role overlaps to determine relationship
        common_roles = set(agent1_roles) & set(agent2_roles)
        
        if common_roles:
            return "Peer with shared expertise"
        elif "supervisor" in agent1_roles and "worker" in agent2_roles:
            return "Subordinate agent"
        elif "worker" in agent1_roles and "supervisor" in agent2_roles:
            return "Manager agent"
        elif any(role in agent2_roles for role in ["audio", "speech", "voice"]):
            return "Audio specialist"
        elif any(role in agent2_roles for role in ["image", "vision"]):
            return "Visual specialist"
        elif any(role in agent2_roles for role in ["video"]):
            return "Video specialist"
        else:
            return "Colleague with different expertise"
    
    def update_relationship(self, from_agent: str, to_agent: str, 
                          trust_delta: float = 0.0, 
                          interaction_type: str = "message") -> None:
        """Update the relationship between two agents.
        
        Args:
            from_agent: The sending agent name
            to_agent: The receiving agent name
            trust_delta: Change in trust level (-0.1 to 0.1)
            interaction_type: Type of interaction (message, handoff, etc.)
        """
        if from_agent not in self.relationships or to_agent not in self.relationships[from_agent]:
            return
            
        # Update trust level (clamped between 0 and 1)
        current_trust = self.relationships[from_agent][to_agent]["trust_level"]
        new_trust = max(0.0, min(1.0, current_trust + trust_delta))
        self.relationships[from_agent][to_agent]["trust_level"] = new_trust
        
        # Update interaction count
        self.relationships[from_agent][to_agent]["interaction_count"] += 1
        
        # Update last interaction time
        self.relationships[from_agent][to_agent]["last_interaction"] = time.time()
        
        # Update in cognitive state if available
        if from_agent in self.agents:
            adapter = self.agents[from_agent]["adapter"]
            if hasattr(adapter, 'cognitive_state') and "mental_state" in adapter.cognitive_state:
                if "accessible_agents" in adapter.cognitive_state["mental_state"]:
                    for agent_info in adapter.cognitive_state["mental_state"]["accessible_agents"]:
                        if agent_info["name"] == to_agent:
                            agent_info["trust_level"] = new_trust
                            break
    
    def get_agent(self, name: str) -> Optional[CognitiveAgentProtocol]:
        """Get an agent by name.
        
        Args:
            name: The name of the agent
            
        Returns:
            The agent protocol adapter, or None if not found
        """
        if name in self.agents:
            return self.agents[name]["adapter"]
        return None
    
    def send_message(self, from_agent: str, to_agent: str, message: str, 
                   session_id: Optional[str] = None) -> Optional[ActionResponse]:
        """Send a message from one agent to another.
        
        Args:
            from_agent: The sending agent name
            to_agent: The receiving agent name
            message: The message content
            session_id: Optional session ID for conversation tracking
            
        Returns:
            The response from the receiving agent, or None if sending failed
        """
        # Get the receiving agent
        receiver = self.get_agent(to_agent)
        if not receiver:
            logger.error(f"Agent '{to_agent}' not found in registry")
            return None
            
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            
        # Create an action request
        request = ActionRequest(
            content=message,
            session_id=session_id,
            role=MessageRole.USER,
            metadata={
                "source_agent": from_agent,
                "is_agent_communication": True
            }
        )
        
        # Log the interaction if display is enabled
        if self.communication_display:
            logger.info(f"Agent Communication: {from_agent} -> {to_agent}: {message[:100]}...")
            
        # Update relationship data
        self.update_relationship(from_agent, to_agent, interaction_type="message")
        
        # Process the request with the receiving agent
        try:
            response = receiver.act(request)
            return response
        except Exception as e:
            logger.error(f"Error sending message from {from_agent} to {to_agent}: {str(e)}")
            return None

        if self.use_mtls and from_agent in self.secure_clients:
            try:
                # Get agent endpoint from metadata
                to_agent_adapter = self.agents[to_agent]["adapter"]
                endpoint = to_agent_adapter.metadata.get("endpoint")
                
                if not endpoint:
                    logger.error(f"Agent {to_agent} does not have an endpoint configured")
                    return None
                
                # Create request payload
                request_data = {
                    "content": message,
                    "session_id": session_id or str(uuid.uuid4()),
                    "role": "user",
                    "metadata": {
                        "source_agent": from_agent,
                        "is_agent_communication": True
                    }
                }
                
                # Make secure request
                secure_client = self.secure_clients[from_agent]
                response = secure_client.request(
                    method="POST",
                    url=f"{endpoint}/act",
                    json=request_data
                )
                
                # Parse response
                if response.status_code == 200:
                    response_data = response.json()
                    return ActionResponse(**response_data)
                else:
                    logger.error(f"Error sending message: {response.status_code} {response.text}")
                    return None
            
            except Exception as e:
                logger.error(f"Error in secure communication: {str(e)}")
                # Fall back to direct method if secure communication fails
                logger.warning("Falling back to direct method call")
    
    def handoff(self, from_agent: str, to_agent: str, context: Dict[str, Any], 
              session_id: Optional[str] = None) -> bool:
        """Handoff a conversation from one agent to another.
        
        Args:
            from_agent: The sending agent name
            to_agent: The receiving agent name
            context: The conversation context to handoff
            session_id: Optional session ID for conversation tracking
            
        Returns:
            True if handoff was successful, False otherwise
        """
        # Get the receiving agent
        receiver = self.get_agent(to_agent)
        if not receiver:
            logger.error(f"Agent '{to_agent}' not found in registry")
            return False
            
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            
        # Store handoff in history
        self.handoff_history[from_agent].append({
            "timestamp": time.time(),
            "to_agent": to_agent,
            "session_id": session_id,
            "context": context
        })
        
        # Store in conversation context
        self.conversation_context[session_id] = {
            "current_agent": to_agent,
            "previous_agent": from_agent,
            "handoff_time": time.time(),
            "context": context
        }
        
        # Log the handoff if display is enabled
        if self.communication_display:
            logger.info(f"Agent Handoff: {from_agent} -> {to_agent} (Session: {session_id})")
            
        # Update relationship data
        self.update_relationship(from_agent, to_agent, trust_delta=0.05, interaction_type="handoff")
        
        return True
    
    def find_agent_by_capability(self, capability: str) -> Optional[str]:
        """Find an agent that has a specific capability.
        
        Args:
            capability: The capability to search for
            
        Returns:
            The name of an agent with the capability, or None if not found
        """
        for name, info in self.agents.items():
            if capability in info["capabilities"]:
                return name
        return None
    
    def find_agent_by_role(self, role: str) -> Optional[str]:
        """Find an agent that has a specific role.
        
        Args:
            role: The role to search for
            
        Returns:
            The name of an agent with the role, or None if not found
        """
        for name, info in self.agents.items():
            if role in info["roles"]:
                return name
        return None