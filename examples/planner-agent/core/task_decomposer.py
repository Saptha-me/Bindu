"""Task decomposition logic - breaks complex goals into sub-tasks."""

from typing import List, Dict


class TaskDecomposer:
    """
    Decomposes complex goals into executable sub-tasks.
    
    Currently uses rule-based pattern matching.
    Can be enhanced with AI (Claude/GPT) for more intelligent decomposition.
    """
    
    def decompose(self, goal: str) -> List[Dict]:
        """
        Decompose a high-level goal into sub-tasks.
        
        Args:
            goal: User's high-level objective
        
        Returns:
            List of sub-task dictionaries with structure:
            [
                {
                    "step": 1,
                    "description": "Task description",
                    "required_capabilities": ["capability1", "capability2"]
                },
                ...
            ]
        """
        # Use rule-based decomposition for MVP
        # TODO: Add AI-powered decomposition using Anthropic Claude
        return self._decompose_rule_based(goal)
    
    def _decompose_rule_based(self, goal: str) -> List[Dict]:
        """
        Simple pattern matching for common task types.
        
        Patterns:
        - "summary/summarize" → research + summarize
        - "report" → research + analyze + write
        - "compare" → research multiple + compare
        - Default → single general task
        """
        keywords = goal.lower()
        tasks = []
        
        if "summary" in keywords or "summarize" in keywords:
            tasks.append({
                "step": 1,
                "description": "Research and retrieve relevant information",
                "required_capabilities": ["research", "web_search"]
            })
            tasks.append({
                "step": 2,
                "description": f"Summarize the information: {goal}",
                "required_capabilities": ["text_summarization", "content_structuring"]
            })
        
        elif "report" in keywords:
            tasks.append({
                "step": 1,
                "description": "Gather comprehensive research data",
                "required_capabilities": ["research", "web_search"]
            })
            tasks.append({
                "step": 2,
                "description": "Analyze and structure findings",
                "required_capabilities": ["text_summarization", "content_structuring"]
            })
        
        elif "compare" in keywords or "comparison" in keywords:
            tasks.append({
                "step": 1,
                "description": "Research first subject",
                "required_capabilities": ["research", "web_search"]
            })
            tasks.append({
                "step": 2,
                "description": "Research second subject",
                "required_capabilities": ["research", "web_search"]
            })
            tasks.append({
                "step": 3,
                "description": "Compare and contrast findings",
                "required_capabilities": ["text_summarization", "content_structuring"]
            })
        
        else:
            # Default: single task for simple requests
            tasks.append({
                "step": 1,
                "description": goal,
                "required_capabilities": ["general"]
            })
        
        return tasks
