from typing import List, Dict, Any, Tuple
from models.agent_profile import AgentProfile
from models.task import SubTask
from .logger import get_logger


def match_capabilities(required: List[str], available: List[str]) -> bool:

    required_set = set(required)
    available_set = set(available)
    return required_set.issubset(available_set)


def score_agent(agent: AgentProfile, subtask: SubTask) -> float:

    logger = get_logger(__name__)
    
    # Check if agent has required capabilities
    if not agent.has_all_capabilities(subtask.required_capabilities):
        return 0.0
    
    # Calculate score based on multiple factors
    score = 0.0
    
    # Reputation (40% weight)
    score += agent.reputation_score * 0.4
    
    # Quality score (30% weight)
    score += agent.average_quality_score * 0.3
    
    # Success rate (20% weight)
    score += agent.get_success_rate() * 0.2
    
    # Availability (10% weight)
    availability = 1.0 if agent.is_available() else 0.0
    score += availability * 0.1
    
    logger.debug(f"Agent {agent.did} scored {score:.2f} for subtask {subtask.id}")
    
    return score


def find_best_matching_agent(agents: List[AgentProfile], 
                            subtask: SubTask) -> Tuple[AgentProfile, float]:

    logger = get_logger(__name__)
    
    best_agent = None
    best_score = -1
    
    for agent in agents:
        score = score_agent(agent, subtask)
        if score > best_score:
            best_score = score
            best_agent = agent
    
    if best_agent:
        logger.info(f"Best agent for subtask {subtask.id}: {best_agent.did} (score: {best_score:.2f})")
    else:
        logger.warning(f"No suitable agent found for subtask {subtask.id}")
    
    return best_agent, best_score