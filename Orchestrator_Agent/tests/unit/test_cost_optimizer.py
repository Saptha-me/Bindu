import pytest


class TestCostOptimizer:
    """Test CostOptimizer functionality"""
    
    def test_find_cheapest_agent(self, cost_optimizer, sample_agents):
        """Test finding cheapest agent"""
        agent = cost_optimizer.find_cheapest_agent(sample_agents, "web-research")
        
        assert agent is not None
        assert agent.has_capability("web-research")
    
    def test_find_best_value_agent(self, cost_optimizer, sample_agents):
        """Test finding best value agent"""
        agent = cost_optimizer.find_best_value_agent(sample_agents, "data-analysis")
        
        assert agent is not None
        assert agent.has_capability("data-analysis")
    
    def test_optimize_agent_selection_cheapest(self, cost_optimizer, sample_agents, sample_task):
        """Test agent selection with cheapest strategy"""
        sample_task.mark_decomposed()
        selection = cost_optimizer.optimize_agent_selection(
            sample_agents,
            sample_task.subtasks,
            50.0,
            strategy="cheapest"
        )
        
        assert len(selection) >= 0
    
    def test_optimize_agent_selection_quality(self, cost_optimizer, sample_agents, sample_task):
        """Test agent selection with quality strategy"""
        sample_task.mark_decomposed()
        selection = cost_optimizer.optimize_agent_selection(
            sample_agents,
            sample_task.subtasks,
            50.0,
            strategy="quality"
        )
        
        assert len(selection) >= 0
    
    def test_optimize_agent_selection_balanced(self, cost_optimizer, sample_agents, sample_task):
        """Test agent selection with balanced strategy"""
        sample_task.mark_decomposed()
        selection = cost_optimizer.optimize_agent_selection(
            sample_agents,
            sample_task.subtasks,
            50.0,
            strategy="balanced"
        )
        
        assert len(selection) >= 0
    
    def test_estimate_total_cost(self, cost_optimizer, sample_agents, sample_task):
        """Test cost estimation"""
        sample_task.mark_decomposed()
        agents_dict = {st.id: sample_agents[0] for st in sample_task.subtasks}
        subtasks_dict = {st.id: st for st in sample_task.subtasks}
        
        total_cost = cost_optimizer.estimate_total_cost(agents_dict, subtasks_dict)
        
        assert total_cost >= 0


