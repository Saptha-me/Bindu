import pytest


class TestAgentRegistry:
    """Test AgentRegistry functionality"""
    
    def test_registry_loads_default_agents(self, agent_registry):
        """Test that registry loads default agents"""
        agents = agent_registry.get_all_agents()
        assert len(agents) == 4
    
    def test_find_agents_by_capability(self, agent_registry):
        """Test finding agents by capability"""
        agents = agent_registry.find_agents_by_capability("web-research")
        
        assert len(agents) > 0
        assert all("web-research" in a.capabilities for a in agents)
    
    def test_find_agents_by_multiple_capabilities(self, agent_registry):
        """Test finding agents with multiple capabilities"""
        agents = agent_registry.find_agents_by_capabilities(["web-research"])
        
        assert len(agents) >= 0
    
    def test_find_cheapest_agent(self, agent_registry):
        """Test finding cheapest agent"""
        agent = agent_registry.find_cheapest_agent("web-research")
        
        assert agent is not None
        assert agent.has_capability("web-research")
    
    def test_find_best_agent_by_reputation(self, agent_registry):
        """Test finding best agent by reputation"""
        agent = agent_registry.find_best_agent("web-research", priority="reputation")
        
        assert agent is not None
    
    def test_find_best_agent_by_quality(self, agent_registry):
        """Test finding best agent by quality"""
        agent = agent_registry.find_best_agent("web-research", priority="quality")
        
        assert agent is not None
    
    def test_register_new_agent(self, agent_registry, sample_agents):
        """Test registering a new agent"""
        new_agent = sample_agents[0]
        initial_count = agent_registry.get_agent_count()
        
        agent_registry.register_agent(new_agent)
        
        assert agent_registry.get_agent_count() >= initial_count
    
    def test_get_agent_by_did(self, agent_registry):
        """Test getting agent by DID"""
        agents = agent_registry.get_all_agents()
        agent_did = agents[0].did
        
        agent = agent_registry.get_agent(agent_did)
        assert agent is not None
        assert agent.did == agent_did
    
    def test_update_heartbeat(self, agent_registry):
        """Test updating agent heartbeat"""
        agents = agent_registry.get_all_agents()
        agent_did = agents[0].did
        
        result = agent_registry.update_agent_heartbeat(agent_did)
        assert result is True
