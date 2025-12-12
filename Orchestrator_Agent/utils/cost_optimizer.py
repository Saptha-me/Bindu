from typing import List, Optional, Dict, Any
from models.agent_profile import AgentProfile
from models.task import SubTask
from .logger import get_logger


class CostOptimizer:
    """Optimizes agent selection by cost and quality"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def find_cheapest_agent(self, agents: List[AgentProfile], 
                           capability: str) -> Optional[AgentProfile]:

        suitable_agents = []
        
        for agent in agents:
            if agent.has_capability(capability):
                cost = agent.get_capability_cost(capability)
                if cost:
                    suitable_agents.append((agent, cost))
        
        if not suitable_agents:
            self.logger.warning(f"No agents found with capability {capability}")
            return None
        
        # Sort by cost and return cheapest
        suitable_agents.sort(key=lambda x: x[1])
        best_agent = suitable_agents[0][0]
        
        self.logger.info(f"Selected cheapest agent: {best_agent.did} (${suitable_agents[0][1]})")
        return best_agent
    
    def find_best_value_agent(self, agents: List[AgentProfile], 
                             capability: str) -> Optional[AgentProfile]:

        suitable_agents = []
        
        for agent in agents:
            if agent.has_capability(capability):
                cost = agent.get_capability_cost(capability)
                if cost and cost > 0:
                    # Cost-to-quality ratio (lower is better)
                    ratio = cost / agent.average_quality_score
                    suitable_agents.append((agent, ratio, cost))
        
        if not suitable_agents:
            return None
        
        # Sort by ratio and return best value
        suitable_agents.sort(key=lambda x: x[1])
        best_agent = suitable_agents[0][0]
        
        self.logger.info(f"Selected best value agent: {best_agent.did}")
        return best_agent
    
    def optimize_agent_selection(self, agents: List[AgentProfile], 
                                subtasks: List[SubTask],
                                budget: float,
                                strategy: str = "balanced") -> Dict[str, AgentProfile]:

        self.logger.info(f"Optimizing agent selection with {strategy} strategy")
        
        selection = {}
        spent = 0.0
        
        for subtask in subtasks:
            suitable = [a for a in agents if a.has_all_capabilities(subtask.required_capabilities)]
            
            if not suitable:
                self.logger.warning(f"No suitable agent for subtask {subtask.id}")
                continue
            
            if strategy == "cheapest":
                selected = min(suitable, key=lambda a: a.estimate_cost(subtask.required_capabilities))
            elif strategy == "quality":
                selected = max(suitable, key=lambda a: a.average_quality_score)
            else:  # balanced
                # Balance cost and quality
                scores = []
                for agent in suitable:
                    cost = agent.estimate_cost(subtask.required_capabilities)
                    quality = agent.average_quality_score
                    score = (quality / cost) if cost > 0 else 0
                    scores.append((agent, score))
                selected = max(scores, key=lambda x: x[1])[0]
            
            selection[subtask.id] = selected
            spent += selected.estimate_cost(subtask.required_capabilities)
        
        self.logger.info(f"Selected {len(selection)} agents, estimated cost: ${spent:.2f}")
        return selection
    
    def estimate_total_cost(self, agents: Dict[str, AgentProfile], 
                           subtasks: Dict[str, SubTask]) -> float:
        """Estimate total cost for an assignment"""
        total = 0.0
        
        for subtask_id, agent in agents.items():
            subtask = subtasks.get(subtask_id)
            if subtask:
                total += agent.estimate_cost(subtask.required_capabilities)
        
        return total