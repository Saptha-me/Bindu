import pytest
from models.task import Task, TaskPriority


class TestTaskDecomposer:
    """Test TaskDecomposer functionality"""
    
    def test_decompose_creates_subtasks(self, task_decomposer, sample_task):
        """Test that decompose creates subtasks"""
        subtasks = task_decomposer.decompose(sample_task)
        
        assert len(subtasks) > 0
        assert len(subtasks) == len(sample_task.required_capabilities)
        assert sample_task.status.value == "decomposed"
    
    def test_decompose_distributes_budget(self, task_decomposer, sample_task):
        """Test that budget is distributed across subtasks"""
        subtasks = task_decomposer.decompose(sample_task)
        
        total_budget = sum(st.max_budget for st in subtasks)
        assert total_budget <= sample_task.max_budget
    
    def test_decompose_assigns_capabilities(self, task_decomposer, sample_task):
        """Test that capabilities are assigned to subtasks"""
        subtasks = task_decomposer.decompose(sample_task)
        
        all_capabilities = set()
        for subtask in subtasks:
            all_capabilities.update(subtask.required_capabilities)
        
        assert all_capabilities == set(sample_task.required_capabilities)
    
    def test_validate_decomposition_success(self, task_decomposer, sample_task):
        """Test successful decomposition validation"""
        task_decomposer.decompose(sample_task)
        
        is_valid, message = task_decomposer.validate_decomposition(sample_task)
        assert is_valid is True
        assert "valid" in message.lower()
    
    def test_validate_decomposition_no_subtasks(self, task_decomposer):
        """Test validation fails with no subtasks"""
        task = Task(
            title="Empty Task",
            description="Task with no subtasks",
            objective="Test",
            required_capabilities=["test"],
            max_budget=50.0
        )
        
        is_valid, message = task_decomposer.validate_decomposition(task)
        assert is_valid is False
    
    def test_replan_failed_subtasks(self, task_decomposer, sample_task):
        """Test replanning of failed subtasks"""
        subtasks = task_decomposer.decompose(sample_task)
        failed_id = subtasks[0].id
        
        new_subtasks = task_decomposer.replan_failed_subtasks(sample_task, [failed_id])
        
        assert len(new_subtasks) > 0
        assert new_subtasks[0].description.startswith("[RETRY]")
    
    def test_estimate_total_duration(self, task_decomposer, sample_task):
        """Test duration estimation"""
        task_decomposer.decompose(sample_task)
        
        duration = task_decomposer.estimate_total_duration(sample_task)
        assert duration > 0
    
    def test_estimate_total_cost(self, task_decomposer, sample_task):
        """Test cost estimation"""
        task_decomposer.decompose(sample_task)
        
        cost = task_decomposer.estimate_total_cost(sample_task)
        assert cost > 0
        assert cost <= sample_task.max_budget
