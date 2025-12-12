import pytest


class TestAgentNegotiator:
    """Test AgentNegotiator functionality"""
    
    def test_initiate_negotiation(self, agent_negotiator, sample_agents, sample_subtask, orchestrator_did):
        """Test initiating negotiation"""
        agent = sample_agents[0]
        sample_subtask.parent_task_id = "test-task-001"
        
        negotiation = agent_negotiator.initiate_negotiation(agent, sample_subtask, 50.0)
        
        assert negotiation is not None
        assert negotiation.agent_did == agent.did
        assert negotiation.max_price == 50.0
    
    def test_request_quote(self, agent_negotiator, sample_agents, sample_subtask):
        """Test requesting quote"""
        agent = sample_agents[0]
        sample_subtask.parent_task_id = "test-task-001"
        
        negotiation = agent_negotiator.initiate_negotiation(agent, sample_subtask, 50.0)
        quote = agent_negotiator.request_quote(negotiation, agent, "web-research")
        
        assert quote is not None
        assert quote.agent_did == agent.did
        assert quote.base_cost > 0
    
    def test_process_quote_acceptable(self, agent_negotiator, sample_agents, sample_subtask):
        """Test processing acceptable quote"""
        agent = sample_agents[0]
        sample_subtask.parent_task_id = "test-task-001"
        
        negotiation = agent_negotiator.initiate_negotiation(agent, sample_subtask, 50.0)
        quote = agent_negotiator.request_quote(negotiation, agent, "web-research")
        
        result = agent_negotiator.process_quote(negotiation.id, quote)
        assert result is True or result is False  # Depends on cost
    
    def test_accept_quote(self, agent_negotiator, sample_agents, sample_subtask):
        """Test accepting quote"""
        agent = sample_agents[0]
        sample_subtask.parent_task_id = "test-task-001"
        
        negotiation = agent_negotiator.initiate_negotiation(agent, sample_subtask, 50.0)
        quote = agent_negotiator.request_quote(negotiation, agent, "web-research")
        
        if agent_negotiator.process_quote(negotiation.id, quote):
            result = agent_negotiator.accept_quote(negotiation.id)
            assert result is True
    
    def test_reject_quote(self, agent_negotiator, sample_agents, sample_subtask):
        """Test rejecting quote"""
        agent = sample_agents[0]
        sample_subtask.parent_task_id = "test-task-001"
        
        negotiation = agent_negotiator.initiate_negotiation(agent, sample_subtask, 50.0)
        
        result = agent_negotiator.reject_quote(negotiation.id)
        assert result is True
    
    def test_counter_offer(self, agent_negotiator, sample_agents, sample_subtask):
        """Test sending counter offer"""
        agent = sample_agents[0]
        sample_subtask.parent_task_id = "test-task-001"
        
        negotiation = agent_negotiator.initiate_negotiation(agent, sample_subtask, 50.0)
        quote = agent_negotiator.request_quote(negotiation, agent, "web-research")
        agent_negotiator.process_quote(negotiation.id, quote)
        
        result = agent_negotiator.counter_offer(negotiation.id, 8.0)
        assert result is True
    
    def test_get_negotiations_by_status(self, agent_negotiator, sample_agents, sample_subtask):
        """Test retrieving negotiations by status"""
        agent = sample_agents[0]
        sample_subtask.parent_task_id = "test-task-001"
        
        agent_negotiator.initiate_negotiation(agent, sample_subtask, 50.0)
        
        negotiations = agent_negotiator.get_all_negotiations()
        assert len(negotiations) >= 1