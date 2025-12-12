import pytest


class TestOrchestratorWorkflow:
    """Test complete orchestrator workflow"""
    
    def test_complete_workflow(
        self,
        task_decomposer,
        agent_registry,
        agent_negotiator,
        agent_executor,
        result_aggregator,
        sample_task
    ):
        """Test complete orchestration workflow"""
        # Step 1: Decompose task
        subtasks = task_decomposer.decompose(sample_task)
        assert len(subtasks) > 0
        
        # Step 2: Get agents from registry
        agents = agent_registry.get_all_agents()
        assert len(agents) > 0
        
        # Step 3: Negotiate with agents
        for subtask in subtasks[:1]:  # Test with first subtask
            agent = agents[0]
            negotiation = agent_negotiator.initiate_negotiation(agent, subtask, 50.0)
            assert negotiation is not None
        
        # Step 4: Execute tasks
        results = {}
        for subtask in subtasks:
            if subtask.required_capabilities:
                agent = agent_registry.find_agents_by_capability(
                    subtask.required_capabilities[0]
                )
                if agent:
                    result = agent_executor.execute_subtask(agent[0].did, subtask)
                    results[subtask.id] = result
        
        # Step 5: Aggregate results
        if results:
            aggregated = result_aggregator.aggregate(sample_task, results)
            assert aggregated is not None
            assert aggregated.task_id == sample_task.id
    
    def test_agent_discovery_and_selection(self, agent_registry, sample_task):
        """Test agent discovery and selection"""
        for capability in sample_task.required_capabilities:
            agents = agent_registry.find_agents_by_capability(capability)
            assert len(agents) > 0
            
            best_agent = agent_registry.find_best_agent(capability, priority="reputation")
            assert best_agent is not None
    
    def test_negotiation_workflow(self, agent_negotiator, agent_registry, sample_task):
        """Test negotiation workflow"""
        sample_task.mark_decomposed()
        
        for subtask in sample_task.subtasks[:1]:
            agents = agent_registry.get_all_agents()
            if agents:
                agent = agents[0]
                
                # Initiate
                negotiation = agent_negotiator.initiate_negotiation(agent, subtask, 50.0)
                
                # Request quote
                if subtask.required_capabilities:
                    quote = agent_negotiator.request_quote(
                        negotiation,
                        agent,
                        subtask.required_capabilities[0]
                    )
                    
                    if quote:
                        # Process and accept
                        agent_negotiator.process_quote(negotiation.id, quote)
                        agent_negotiator.accept_quote(negotiation.id)
    
    def test_execution_and_aggregation(
        self,
        task_decomposer,
        agent_executor,
        result_aggregator,
        sample_task
    ):
        """Test execution and result aggregation"""
        # Decompose
        subtasks = task_decomposer.decompose(sample_task)
        
        # Execute
        results = {}
        for subtask in subtasks:
            result = agent_executor.execute_subtask("did:bindu:agent:test", subtask)
            results[subtask.id] = result
        
        # Aggregate
        aggregated = result_aggregator.aggregate(sample_task, results)
        
        assert aggregated.task_id == sample_task.id
        assert len(aggregated.subtask_results) == len(subtasks)
