"""Result aggregation from multiple worker agents."""

from typing import List, Dict


class Aggregator:
    """
    Merges results from multiple worker agents into coherent output.
    
    Handles both successful and failed task executions.
    """
    
    def merge(self, results: List[Dict], original_goal: str) -> str:
        """
        Merge execution results into user-friendly output.
        
        Args:
            results: List of execution results from worker agents
            original_goal: User's original goal/request
        
        Returns:
            Formatted string with orchestration summary and results
        """
        successful = [r for r in results if r["result"].get("success")]
        failed = [r for r in results if not r["result"].get("success")]
        
        output_parts = []
        
        # Header
        output_parts.append(f"✅ **Orchestration Complete**\n")
        output_parts.append(f"**Goal:** {original_goal}\n")
        output_parts.append(f"**Tasks Executed:** {len(successful)}/{len(results)}\n")
        
        # Successful task results
        if successful:
            output_parts.append("\n---\n")
            for item in successful:
                output_parts.append(f"\n### Step {item['step']}: {item['description']}\n")
                output_parts.append(item["result"]["content"])
                output_parts.append("\n")
        
        # Failed tasks (if any)
        if failed:
            output_parts.append("\n---\n")
            output_parts.append("\n⚠️ **Some tasks failed:**\n")
            for item in failed:
                error_msg = item["result"].get("error", "Unknown error")
                output_parts.append(f"- **Step {item['step']}:** {item['description']}")
                output_parts.append(f"  - Error: {error_msg}\n")
        
        # Footer
        output_parts.append("\n---\n")
        output_parts.append("*Orchestrated by Planner Agent*")
        
        return "\n".join(output_parts)
