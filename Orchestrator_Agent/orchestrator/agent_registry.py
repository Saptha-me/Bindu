import logging
from typing import List, Optional, Dict, Any
from models.agent_profile import AgentProfile, AgentCapability
from utils.logger import get_logger


class AgentRegistry:
    """Manages agent discovery and registration"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self.agents: Dict[str, AgentProfile] = {}
        self._load_default_agents()
    
    def _load_default_agents(self) -> None:
        """Load default agents for demo purposes"""
        # Research Agent
        research_agent = AgentProfile(
            did="did:bindu:agent:research:001",
            name="Research Agent",
            description="Performs web research and information gathering",
            owner="research-team@bindu.io",
            endpoint_url="http://localhost:3001"
        )
        research_agent.add_capability(AgentCapability(
            name="web-research",
            description="Search and gather information from web",
            cost_per_call=5.0,
            success_rate=0.98,
            avg_execution_time=60
        ))
        self.agents[research_agent.did] = research_agent
        
        # Analysis Agent
        analysis_agent = AgentProfile(
            did="did:bindu:agent:analysis:001",
            name="Analysis Agent",
            description="Performs data analysis and insights generation",
            owner="analysis-team@bindu.io",
            endpoint_url="http://localhost:3002"
        )
        analysis_agent.add_capability(AgentCapability(
            name="data-analysis",
            description="Analyze data and generate insights",
            cost_per_call=10.0,
            success_rate=0.96,
            avg_execution_time=90
        ))
        self.agents[analysis_agent.did] = analysis_agent
        
        # Generation Agent
        generation_agent = AgentProfile(
            did="did:bindu:agent:generation:001",
            name="Generation Agent",
            description="Generates content and reports",
            owner="generation-team@bindu.io",
            endpoint_url="http://localhost:3003"
        )
        generation_agent.add_capability(AgentCapability(
            name="text-generation",
            description="Generate reports and content",
            cost_per_call=8.0,
            success_rate=0.94,
            avg_execution_time=120
        ))
        self.agents[generation_agent.did] = generation_agent
        
        # Verification Agent
        verification_agent = AgentProfile(
            did="did:bindu:agent:verification:001",
            name="Verification Agent",
            description="Verifies accuracy and quality of results",
            owner="verification-team@bindu.io",
            endpoint_url="http://localhost:3004"
        )
        verification_agent.add_capability(AgentCapability(
            name="quality-check",
            description="Verify accuracy and quality",
            cost_per_call=7.0,
            success_rate=0.99,
            avg_execution_time=45
        ))
        self.agents[verification_agent.did] = verification_agent
        
        self.logger.info(f"Loaded {len(self.agents)} default agents")
    
    def register_agent(self, agent: AgentProfile) -> bool:
        """Register a new agent"""
        if agent.did in self.agents:
            self.logger.warning(f"Agent {agent.did} already registered")
            return False
        
        self.agents[agent.did] = agent
        self.logger.info(f"Registered agent {agent.did}")
        return True
    
    def unregister_agent(self, agent_did: str) -> bool:
        """Unregister an agent"""
        if agent_did in self.agents:
            del self.agents[agent_did]
            self.logger.info(f"Unregistered agent {agent_did}")
            return True
        return False
    
    def get_agent(self, agent_did: str) -> Optional[AgentProfile]:
        """Get agent by DID"""
        return self.agents.get(agent_did)
    
    def find_agents_by_capability(self, capability_name: str) -> List[AgentProfile]:
        """Find all agents with a specific capability"""
        agents = []
        for agent in self.agents.values():
            if agent.has_capability(capability_name):
                agents.append(agent)
        return agents
    
    def find_agents_by_capabilities(self, capability_names: List[str]) -> List[AgentProfile]:
        """Find agents that have all specified capabilities"""
        agents = []
        for agent in self.agents.values():
            if agent.has_all_capabilities(capability_names):
                agents.append(agent)
        return agents
    
    def find_available_agents(self) -> List[AgentProfile]:
        """Find all available agents"""
        return [agent for agent in self.agents.values() if agent.is_available()]
    
    def find_cheapest_agent(self, capability_name: str) -> Optional[AgentProfile]:
        """Find cheapest agent for a capability"""
        agents = self.find_agents_by_capability(capability_name)
        if not agents:
            return None
        
        # Get cost for capability and find minimum
        agents_with_cost = []
        for agent in agents:
            cost = agent.get_capability_cost(capability_name)
            if cost:
                agents_with_cost.append((agent, cost))
        
        if not agents_with_cost:
            return None
        
        return min(agents_with_cost, key=lambda x: x[1])[0]
    
    def find_best_agent(self, capability_name: str, priority: str = "reputation") -> Optional[AgentProfile]:
        """
        Find best agent for a capability
        
        Args:
            capability_name: Capability required
            priority: "reputation", "quality", "speed", or "cost"
        """
        agents = self.find_agents_by_capability(capability_name)
        if not agents:
            return None
        
        if priority == "reputation":
            return max(agents, key=lambda a: a.reputation_score)
        elif priority == "quality":
            return max(agents, key=lambda a: a.average_quality_score)
        elif priority == "speed":
            return min(agents, key=lambda a: a.response_time_ms)
        elif priority == "cost":
            return self.find_cheapest_agent(capability_name)
        
        return agents[0]
    
    def get_agent_status(self, agent_did: str) -> Optional[str]:
        """Get agent status"""
        agent = self.get_agent(agent_did)
        if agent:
            return agent.status.value
        return None
    
    def update_agent_heartbeat(self, agent_did: str) -> bool:
        """Update agent heartbeat"""
        agent = self.get_agent(agent_did)
        if agent:
            agent.update_heartbeat()
            return True
        return False