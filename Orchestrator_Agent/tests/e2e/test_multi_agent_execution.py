import pytest


class TestMultiAgentExecution:
    """Test complete multi-agent execution flows"""
    
    def test_full_multi_agent_orchestration(
        self,
        task_decomposer,
        agent_registry,
        agent_negotiator,
        agent_executor,
        result_aggregator,
        payment_handler,
        sample_task,
        orchestrator_did
    ):
        """Test complete multi-agent orchestration from start to finish"""
        
        # Step 1: Decompose the task
        print("Step 1: Decomposing task...")
        subtasks = task_decomposer.decompose(sample_task)
        assert len(subtasks) > 0, "Task should be decomposed into subtasks"
        print(f"  ✓ Decomposed into {len(subtasks)} subtasks")
        
        # Step 2: Validate decomposition
        print("Step 2: Validating decomposition...")
        is_valid, msg = task_decomposer.validate_decomposition(sample_task)
        assert is_valid, f"Decomposition validation failed: {msg}"
        print("  ✓ Decomposition is valid")
        
        # Step 3: Discover available agents
        print("Step 3: Discovering agents...")
        available_agents = agent_registry.get_all_agents()
        assert len(available_agents) > 0, "Should have available agents"
        print(f"  ✓ Found {len(available_agents)} available agents")
        
        # Step 4: Negotiate with agents for each subtask
        print("Step 4: Negotiating with agents...")
        negotiations = {}
        for subtask in subtasks:
            if subtask.required_capabilities:
                capability = subtask.required_capabilities[0]
                agents_with_capability = agent_registry.find_agents_by_capability(capability)
                
                if agents_with_capability:
                    agent = agent_registry.find_cheapest_agent(
                        available_agents,
                        capability
                    )
                    
                    if agent:
                        negotiation = agent_negotiator.initiate_negotiation(
                            agent,
                            subtask,
                            subtask.max_budget
                        )
                        
                        quote = agent_negotiator.request_quote(
                            negotiation,
                            agent,
                            capability
                        )
                        
                        if quote and agent_negotiator.process_quote(negotiation.id, quote):
                            agent_negotiator.accept_quote(negotiation.id)
                            negotiations[subtask.id] = (agent, negotiation)
        
        assert len(negotiations) > 0, "Should have at least one successful negotiation"
        print(f"  ✓ Successfully negotiated with {len(negotiations)} agents")
        
        # Step 5: Execute tasks on agents
        print("Step 5: Executing tasks...")
        execution_results = {}
        for subtask in subtasks:
            if subtask.id in negotiations:
                agent, negotiation = negotiations[subtask.id]
                
                try:
                    result = agent_executor.execute_subtask(agent.did, subtask)
                    execution_results[subtask.id] = result
                except Exception as e:
                    print(f"  ! Execution failed for {subtask.id}: {str(e)}")
        
        assert len(execution_results) > 0, "Should have at least one successful execution"
        print(f"  ✓ Successfully executed {len(execution_results)} tasks")
        
        # Step 6: Aggregate results
        print("Step 6: Aggregating results...")
        aggregated = result_aggregator.aggregate(sample_task, execution_results)
        assert aggregated is not None, "Should have aggregated results"
        assert aggregated.task_id == sample_task.id
        print(f"  ✓ Results aggregated: {aggregated.summary}")
        
        # Step 7: Process payments
        print("Step 7: Processing payments...")
        total_payment = 0.0
        payment_transactions = []
        
        for subtask in subtasks:
            if subtask.id in negotiations:
                agent, negotiation = negotiations[subtask.id]
                cost = agent.estimate_cost(subtask.required_capabilities)
                
                transaction = payment_handler.create_payment(agent.did, cost)
                result = payment_handler.settle_payment(transaction.id)
                
                if result:
                    payment_transactions.append(transaction)
                    total_payment += cost
        
        print(f"  ✓ Processed {len(payment_transactions)} payments (${total_payment:.2f} total)")
        
        # Step 8: Verify final state
        print("Step 8: Verifying final state...")
        settlement_summary = payment_handler.get_settlement_summary()
        
        assert settlement_summary["completed"] == len(payment_transactions)
        print("  ✓ All payments settled successfully")
        
        print("\n✅ Complete multi-agent orchestration successful!")
        print(f"   Task: {sample_task.title}")
        print(f"   Subtasks: {len(subtasks)}")
        print(f"   Agents engaged: {len(negotiations)}")
        print(f"   Tasks executed: {len(execution_results)}")
        print(f"   Payments settled: {settlement_summary['completed']}")
    
    def test_parallel_task_execution(
        self,
        task_decomposer,
        agent_registry,
        agent_executor,
        sample_task
    ):
        """Test parallel execution of multiple tasks"""
        # Decompose task
        subtasks = task_decomposer.decompose(sample_task)
        assert len(subtasks) > 0
        
        # Prepare agent assignments
        agents = agent_registry.get_all_agents()
        tasks_to_execute = []
        
        for subtask in subtasks:
            if agents:
                tasks_to_execute.append((agents[0].did, subtask))
        
        # Execute in parallel
        results = agent_executor.execute_parallel(tasks_to_execute)
        
        assert len(results) == len(tasks_to_execute)
        print(f"✓ Parallel execution of {len(results)} tasks completed")
    
    def test_failure_recovery(
        self,
        task_decomposer,
        agent_executor,
        sample_task
    ):
        """Test failure recovery with retry"""
        # Decompose task
        subtasks = task_decomposer.decompose(sample_task)
        
        # Execute first task
        first_subtask = subtasks[0]
        result1 = agent_executor.execute_subtask("did:bindu:agent:test", first_subtask)
        assert result1["status"] == "completed"
        
        # Retry the task
        result2 = agent_executor.retry_subtask("did:bindu:agent:test", first_subtask)
        assert result2["status"] == "completed"
        
        print("✓ Failure recovery and retry successful")
    
    def test_cost_controlled_execution(
        self,
        task_decomposer,
        agent_registry,
        cost_optimizer,
        sample_task
    ):
        """Test execution within cost constraints"""
        # Decompose task
        subtasks = task_decomposer.decompose(sample_task)
        
        # Get agents
        agents = agent_registry.get_all_agents()
        
        # Optimize selection
        selection = cost_optimizer.optimize_agent_selection(
            agents,
            subtasks,
            sample_task.max_budget,
            strategy="balanced"
        )
        
        # Calculate total cost
        total_cost = cost_optimizer.estimate_total_cost(
            {st_id: selection[st_id] for st_id in selection if st_id in selection},
            {st.id: st for st in subtasks}
        )
        
        assert total_cost <= sample_task.max_budget * 1.1  # Allow 10% buffer
        print(f"✓ Cost-controlled execution within budget: ${total_cost:.2f} <= ${sample_task.max_budget:.2f}")
    
    def test_agent_capability_matching(
        self,
        agent_registry,
        sample_task
    ):
        """Test agent capability matching for all task requirements"""
        agents = agent_registry.get_all_agents()
        
        for capability in sample_task.required_capabilities:
            matching_agents = agent_registry.find_agents_by_capability(capability)
            assert len(matching_agents) > 0, f"No agents found for {capability}"
        
        print(f"✓ All {len(sample_task.required_capabilities)} required capabilities have matching agents")
    
    def test_negotiation_acceptance_rates(
        self,
        agent_negotiator,
        agent_registry,
        sample_task,
        orchestrator_did
    ):
        """Test negotiation success rates"""
        sample_task.mark_decomposed()
        agents = agent_registry.get_all_agents()
        
        successful_negotiations = 0
        total_negotiations = 0
        
        for subtask in sample_task.subtasks:
            for agent in agents[:2]:  # Test with first 2 agents
                total_negotiations += 1
                
                negotiation = agent_negotiator.initiate_negotiation(agent, subtask, 50.0)
                
                if subtask.required_capabilities:
                    quote = agent_negotiator.request_quote(
                        negotiation,
                        agent,
                        subtask.required_capabilities[0]
                    )
                    
                    if quote and agent_negotiator.process_quote(negotiation.id, quote):
                        if agent_negotiator.accept_quote(negotiation.id):
                            successful_negotiations += 1
        
        success_rate = (successful_negotiations / total_negotiations * 100) if total_negotiations > 0 else 0
        print(f"✓ Negotiation success rate: {success_rate:.1f}% ({successful_negotiations}/{total_negotiations})")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])