"""Tests for task decomposition logic."""

import pytest
from core.task_decomposer import TaskDecomposer


def test_decompose_summary_task():
    """Test decomposition of summarization requests."""
    
    decomposer = TaskDecomposer()
    tasks = decomposer.decompose("Create a summary of recent AI developments")
    
    assert len(tasks) == 2
    assert tasks[0]["step"] == 1
    assert "research" in tasks[0]["required_capabilities"]
    assert tasks[1]["step"] == 2
    assert "text_summarization" in tasks[1]["required_capabilities"]


def test_decompose_report_task():
    """Test decomposition of report generation requests."""
    
    decomposer = TaskDecomposer()
    tasks = decomposer.decompose("Generate a report on machine learning")
    
    assert len(tasks) == 2
    assert any("research" in t["required_capabilities"] for t in tasks)


def test_decompose_comparison_task():
    """Test decomposition of comparison requests."""
    
    decomposer = TaskDecomposer()
    tasks = decomposer.decompose("Compare Python and JavaScript")
    
    assert len(tasks) == 3  # Research A, Research B, Compare
    assert tasks[2]["step"] == 3


def test_decompose_simple_task():
    """Test decomposition of simple single-step task."""
    
    decomposer = TaskDecomposer()
    tasks = decomposer.decompose("What is the weather today?")
    
    assert len(tasks) == 1
    assert tasks[0]["step"] == 1
    assert "general" in tasks[0]["required_capabilities"]


def test_decompose_returns_valid_structure():
    """Test that all decomposed tasks have required fields."""
    
    decomposer = TaskDecomposer()
    tasks = decomposer.decompose("Test goal")
    
    for task in tasks:
        assert "step" in task
        assert "description" in task
        assert "required_capabilities" in task
        assert isinstance(task["required_capabilities"], list)
