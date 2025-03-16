from typing import Dict, List, Any, Optional, Union
import json
from datetime import datetime
from .agent import BaseAgent

class CognitiveAgent(BaseAgent):
    """
    Cognitive Agent implementation for Pebble inspired by Microsoft's TinyTroupe.
    This agent has cognitive functions like act, think, see, listen, and memory management.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Cognitive state
        self.cognitive_state = {
            "datetime": datetime.now().isoformat(),
            "location": None,
            "context": [],
            "goals": [],
            "attention": None,
            "emotions": "Neutral",
            "memory_context": None,
            "accessible_agents": []
        }
        
        # Episodic memory for storing experiences
        self.episodic_memory = {
            "experiences": [],
            "recent_interactions": [],
            "important_events": []
        }
        
        # Tracking of actions
        self.action_buffer = []
        self.MAX_ACTIONS_BEFORE_DONE = 15  # Prevent infinite action loops
        
    def act(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Execute an action based on the current cognitive state and prompt.
        
        Args:
            prompt: The action prompt
            **kwargs: Additional arguments
            
        Returns:
            Response with action results
        """
        # Record action in buffer to prevent infinite loops
        self.action_buffer.append({"type": "act", "prompt": prompt, "timestamp": datetime.now().isoformat()})
        
        # Check if we've exceeded the maximum number of actions
        if len(self.action_buffer) > self.MAX_ACTIONS_BEFORE_DONE:
            return {
                "status": "error",
                "error": "Maximum number of actions exceeded",
                "action_count": len(self.action_buffer)
            }
        
        # Process using the base agent's action system
        result = super().act(prompt, **kwargs)
        
        # Add to episodic memory
        self._add_to_episodic_memory({
            "type": "action",
            "content": prompt,
            "result": result.get("response", ""),
            "timestamp": datetime.now().isoformat()
        })
        
        return result
    
    def listen(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """
        Process auditory/text input and update cognitive state.
        
        Args:
            input_text: The text to process
            **kwargs: Additional arguments
            
        Returns:
            Processing results
        """
        # Update attention to the listened content
        self.cognitive_state["attention"] = f"Listening to: {input_text[:50]}..."
        
        # Process the input
        context = self._apply_instructions(input_text)
        memory_context = self._retrieve_memory_context(input_text)
        
        # Add to episodic memory
        self._add_to_episodic_memory({
            "type": "listen",
            "content": input_text,
            "timestamp": datetime.now().isoformat()
        })
        
        # Return processing results
        return {
            "status": "success",
            "processed_input": input_text,
            "context": context,
            "memory_activated": bool(memory_context),
            "cognitive_state": self.cognitive_state
        }
    
    def think(self, thought_prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Process internal thought based on prompt and current cognitive state.
        
        Args:
            thought_prompt: The thinking prompt
            **kwargs: Additional arguments
            
        Returns:
            Thinking results
        """
        # Update cognitive state
        self.cognitive_state["attention"] = f"Thinking about: {thought_prompt[:50]}..."
        
        # Generate thought using the model
        thought_response = self._generate_response(
            prompt=thought_prompt,
            context={"type": "thinking", "cognitive_state": self.cognitive_state},
            **kwargs
        )
        
        # Add to episodic memory
        self._add_to_episodic_memory({
            "type": "thought",
            "content": thought_prompt,
            "result": thought_response,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "status": "success",
            "thought_prompt": thought_prompt,
            "thought_result": thought_response,
            "cognitive_state": self.cognitive_state
        }
    
    def see(self, visual_input: Union[str, Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Process visual input (description or structured data) and update cognitive state.
        
        Args:
            visual_input: Visual input as text description or structured data
            **kwargs: Additional arguments
            
        Returns:
            Processing results
        """
        # Update attention to the visual content
        if isinstance(visual_input, str):
            self.cognitive_state["attention"] = f"Looking at: {visual_input[:50]}..."
            visual_description = visual_input
        else:
            self.cognitive_state["attention"] = "Processing visual information..."
            visual_description = json.dumps(visual_input)
        
        # Process the visual input
        context = self._apply_instructions(visual_description)
        
        # Add to episodic memory
        self._add_to_episodic_memory({
            "type": "visual",
            "content": visual_description,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "status": "success",
            "processed_visual": visual_description,
            "context": context,
            "cognitive_state": self.cognitive_state
        }
    
    def internalize_goal(self, goal: str, **kwargs) -> Dict[str, Any]:
        """
        Set a new goal and internalize it into the cognitive state.
        
        Args:
            goal: The goal to internalize
            **kwargs: Additional arguments
            
        Returns:
            Updated cognitive state
        """
        # Update current goal
        self.current_goal = goal
        
        # Add to goal stack
        self.goal_stack.append(goal)
        
        # Update cognitive state
        self.cognitive_state["goals"] = self.goal_stack
        
        # Add to episodic memory
        self._add_to_episodic_memory({
            "type": "goal_setting",
            "content": goal,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "status": "success",
            "goal": goal,
            "goal_stack": self.goal_stack,
            "cognitive_state": self.cognitive_state
        }
    
    def listen_and_act(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """
        Composite operation: listen to input and then take action.
        
        Args:
            input_text: The text to process
            **kwargs: Additional arguments
            
        Returns:
            Processing and action results
        """
        # First listen
        listen_result = self.listen(input_text, **kwargs)
        
        # Then determine action based on listened content
        action_prompt = f"Based on what I heard: '{input_text}', I should:"
        act_result = self.act(action_prompt, **kwargs)
        
        return {
            "status": "success" if act_result["status"] == "success" else "error",
            "listen_result": listen_result,
            "act_result": act_result,
            "cognitive_state": self.cognitive_state
        }
    
    def see_and_act(self, visual_input: Union[str, Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """
        Composite operation: process visual input and then take action.
        
        Args:
            visual_input: Visual input as text description or structured data
            **kwargs: Additional arguments
            
        Returns:
            Processing and action results
        """
        # First see
        see_result = self.see(visual_input, **kwargs)
        
        # Then determine action based on visual content
        if isinstance(visual_input, str):
            action_prompt = f"Based on what I saw: '{visual_input}', I should:"
        else:
            action_prompt = "Based on the visual information I received, I should:"
        
        act_result = self.act(action_prompt, **kwargs)
        
        return {
            "status": "success" if act_result["status"] == "success" else "error",
            "see_result": see_result,
            "act_result": act_result,
            "cognitive_state": self.cognitive_state
        }
    
    def think_and_act(self, thought_prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Composite operation: think and then take action.
        
        Args:
            thought_prompt: The thinking prompt
            **kwargs: Additional arguments
            
        Returns:
            Thinking and action results
        """
        # First think
        think_result = self.think(thought_prompt, **kwargs)
        
        # Then determine action based on thought
        action_prompt = f"After thinking about '{thought_prompt}', I should:"
        act_result = self.act(action_prompt, **kwargs)
        
        return {
            "status": "success" if act_result["status"] == "success" else "error",
            "think_result": think_result,
            "act_result": act_result,
            "cognitive_state": self.cognitive_state
        }
    
    def update_cognitive_state(self, updates: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Update the agent's cognitive state with provided values.
        
        Args:
            updates: Dictionary of cognitive state updates
            **kwargs: Additional arguments
            
        Returns:
            Updated cognitive state
        """
        # Update cognitive state with provided values
        for key, value in updates.items():
            if key in self.cognitive_state:
                self.cognitive_state[key] = value
        
        # Set timestamp
        self.cognitive_state["datetime"] = datetime.now().isoformat()
        
        # Add to episodic memory
        self._add_to_episodic_memory({
            "type": "cognitive_update",
            "content": updates,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "status": "success",
            "cognitive_state": self.cognitive_state
        }
    
    def retrieve_recent_memories(self, limit: int = 5, **kwargs) -> Dict[str, Any]:
        """
        Retrieve the most recent memories from episodic memory.
        
        Args:
            limit: Maximum number of memories to retrieve
            **kwargs: Additional arguments
            
        Returns:
            Recent memories
        """
        # Get recent memories
        recent_memories = self.episodic_memory["experiences"][-limit:] if self.episodic_memory["experiences"] else []
        
        return {
            "status": "success",
            "recent_memories": recent_memories,
            "count": len(recent_memories)
        }
    
    def retrieve_relevant_memories(self, query: str, limit: int = 5, **kwargs) -> Dict[str, Any]:
        """
        Retrieve memories relevant to the query from episodic memory.
        
        Args:
            query: The search query
            limit: Maximum number of memories to retrieve
            **kwargs: Additional arguments
            
        Returns:
            Relevant memories
        """
        # In a real implementation, we would use semantic search here
        # For now, we'll do a simple keyword match
        relevant_memories = []
        for memory in self.episodic_memory["experiences"]:
            content = memory.get("content", "")
            if isinstance(content, str) and query.lower() in content.lower():
                relevant_memories.append(memory)
            elif isinstance(content, dict) and any(query.lower() in str(v).lower() for v in content.values()):
                relevant_memories.append(memory)
        
        relevant_memories = relevant_memories[-limit:] if len(relevant_memories) > limit else relevant_memories
        
        return {
            "status": "success",
            "query": query,
            "relevant_memories": relevant_memories,
            "count": len(relevant_memories)
        }
    
    def _add_to_episodic_memory(self, memory_entry: Dict[str, Any]):
        """Add an entry to episodic memory."""
        self.episodic_memory["experiences"].append(memory_entry)
        
        # Keep the recent interactions updated
        if memory_entry["type"] in ["action", "listen"]:
            self.episodic_memory["recent_interactions"].append(memory_entry)
            # Trim to last 10 interactions
            if len(self.episodic_memory["recent_interactions"]) > 10:
                self.episodic_memory["recent_interactions"] = self.episodic_memory["recent_interactions"][-10:]
