"""Agent discovery and capability matching via .well-known/agent.json"""

import requests
from typing import List, Dict, Optional


class AgentRegistry:
    """
    Discovers and manages Bindu agents based on their capabilities.
    
    Agents are discovered by fetching their agent cards from
    /.well-known/agent.json endpoint.
    """
    
    def __init__(self, agent_urls: List[str]):
        """
        Initialize registry with agent URLs from environment variable.
        
        Args:
            agent_urls: List of agent base URLs (e.g., ["http://localhost:3775"])
        """
        self.agents = []
        
        for url in agent_urls:
            try:
                card = self._fetch_agent_card(url)
                self.agents.append(card)
                print(f"✅ Registered agent: {card.get('name', 'Unknown')} at {url}")
            except Exception as e:
                print(f"⚠️  Warning: Could not fetch agent card from {url}: {e}")
    
    def find_agent_for_capabilities(self, required_caps: List[str]) -> Optional[Dict]:
        """
        Find the best agent match for required capabilities.
        
        Uses scoring based on overlapping capabilities.
        Best match (highest score) wins.
        
        Args:
            required_caps: List of required capability strings
        
        Returns:
            Agent card dict with highest capability match, or None
        """
        best_match = None
        best_score = 0
        
        for agent in self.agents:
            score = self._match_score(agent, required_caps)
            if score > best_score:
                best_score = score
                best_match = agent
        
        return best_match
    
    def _fetch_agent_card(self, url: str) -> Dict:
        """
        Fetch agent card from /.well-known/agent.json endpoint.
        
        Args:
            url: Base URL of the agent
        
        Returns:
            Agent card dictionary with skills, capabilities, etc.
        """
        response = requests.get(
            f"{url}/.well-known/agent.json",
            timeout=10
        )
        response.raise_for_status()
        
        data = response.json()
        data["url"] = url  # Add URL to card for later execution
        
        return data
    
    def _match_score(self, agent: Dict, required_caps: List[str]) -> int:
        """
        Calculate how well an agent matches required capabilities.
        
        Extracts capabilities from all agent skills and counts overlaps.
        
        Args:
            agent: Agent card dictionary
            required_caps: Required capability list
        
        Returns:
            Number of matching capabilities (0 if no match)
        """
        # Extract all capabilities from agent's skills
        agent_caps = []
        
        for skill in agent.get("skills", []):
            # Skills may have capabilities list
            skill_caps = skill.get("capabilities", [])
            agent_caps.extend(skill_caps)
            
            # Also check tags as fallback
            tags = skill.get("tags", [])
            agent_caps.extend(tags)
        
        # Count overlapping capabilities
        matches = sum(1 for cap in required_caps if cap in agent_caps)
        
        return matches
