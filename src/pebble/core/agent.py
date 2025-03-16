from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Union
import json
from datetime import datetime

@dataclass
class BaseAgent:
    """Base class for all agents in pebble following the 6-section principle."""
    
    # --- Section 1: Instructions and Flow ---
    name: str
    description: str
    instructions: List[str] = field(default_factory=list)
    goal: Optional[str] = None
    markdown: bool = True
    add_datetime_to_instructions: bool = True
    
    # --- Section 2: Memory System ---
    short_term_memory: List[Dict[str, Any]] = field(default_factory=list)
    long_term_memory: Optional[Dict[str, Any]] = None
    memory_window_size: int = 10  # Number of recent interactions to keep in short term memory
    add_history_to_messages: bool = True
    num_history_responses: int = 3
    
    # --- Section 3: Tools System ---
    tools: List[Any] = field(default_factory=list)
    show_tool_calls: bool = False
    tool_call_limit: Optional[int] = None
    tool_choice: Optional[Union[str, Dict[str, Any]]] = None
    
    # --- Section 4: Knowledge System ---
    knowledge_base: Optional[Any] = None
    add_references: bool = True
    references_format: Literal['json', 'yaml'] = 'json'
    search_knowledge: bool = True
    update_knowledge: bool = False
    
    # --- Section 5: Model System ---
    model: Any
    stream: bool = True
    retries: int = 3
    delay_between_retries: int = 1
    structured_outputs: bool = True
    
    # --- Section 6: Goal System ---
    current_goal: Optional[str] = None
    goal_stack: List[str] = field(default_factory=list)
    goal_history: List[Dict[str, Any]] = field(default_factory=list)
    goal_constraints: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize all sections of the agent after dataclass initialization."""
        # Section 1: Instructions and Flow
        if not self.instructions:
            self.instructions = [
                "Follow the goal and constraints provided",
                "Use available tools and knowledge effectively",
                "Maintain context across interactions"
            ]
        
        # Section 2: Memory System
        self._initialize_memory_system()
        
        # Section 3: Tools System
        self._initialize_tools_system()
        
        # Section 4: Knowledge System
        self._initialize_knowledge_system()
        
        # Section 5: Model System
        self._validate_model()
        
        # Section 6: Goal System
        self._initialize_goal_system()
    
    def _initialize_memory_system(self):
        """Initialize the memory systems."""
        self.current_messages = []
        if not self.short_term_memory:
            self.short_term_memory = []
        
        if not self.long_term_memory:
            self.long_term_memory = {
                'interactions': [],
                'learned_concepts': {},
                'important_events': []
            }
    
    def _initialize_tools_system(self):
        """Initialize the tools system."""
        self.tool_calls_history = []
        self.available_tools = {}
        
        # Register each tool
        for tool in self.tools:
            if hasattr(tool, 'name'):
                self.available_tools[tool.name] = tool
    
    def _initialize_knowledge_system(self):
        """Initialize the knowledge system."""
        self.knowledge_cache = {}
        self.recent_references = []
        
        if self.knowledge_base:
            # Initialize knowledge base if provided
            if hasattr(self.knowledge_base, 'initialize'):
                self.knowledge_base.initialize()
    
    def _validate_model(self):
        """Validate the model configuration."""
        if not self.model:
            raise ValueError("Model must be provided")
        
        # Ensure model has required methods
        required_methods = ['generate']
        for method in required_methods:
            if not hasattr(self.model, method):
                raise ValueError(f"Model must implement {method} method")
    
    def _initialize_goal_system(self):
        """Initialize the goal system."""
        if self.goal and not self.current_goal:
            self.current_goal = self.goal
            self.goal_stack.append(self.goal)
        
        self.goal_metrics = {
            'completed_goals': 0,
            'failed_goals': 0,
            'current_progress': 0.0
        }
        
    def act(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Main action method that processes the prompt using all 6 sections of the agent."""
        try:
            # Section 1: Apply Instructions
            context = self._apply_instructions(prompt)
            
            # Section 2: Check Memory
            memory_context = self._retrieve_memory_context(prompt)
            
            # Section 3: Prepare Tools
            available_tools = self._prepare_tools(context)
            
            # Section 4: Get Knowledge
            knowledge_refs = self._get_knowledge_references(prompt)
            
            # Section 5: Generate Response
            for attempt in range(self.retries + 1):
                try:
                    response = self._generate_response(
                        prompt=prompt,
                        context=context,
                        memory_context=memory_context,
                        tools=available_tools,
                        knowledge_refs=knowledge_refs,
                        **kwargs
                    )
                    break
                except Exception as e:
                    if attempt == self.retries:
                        raise e
                    time.sleep(self.delay_between_retries)
            
            # Section 6: Update Goals
            self._update_goals(prompt, response)
            
            # Store interaction in memory
            self._store_interaction(prompt, response, context)
            
            return {
                "status": "success",
                "response": response,
                "context": context,
                "memory_used": bool(memory_context),
                "tools_available": list(available_tools.keys()),
                "knowledge_refs": bool(knowledge_refs),
                "current_goal": self.current_goal,
                "goal_progress": self.goal_metrics['current_progress']
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "current_goal": self.current_goal
            }
    
    def _apply_instructions(self, prompt: str) -> Dict[str, Any]:
        """Apply agent instructions to create context."""
        context = {
            'timestamp': datetime.now().isoformat(),
            'instructions': self.instructions,
            'constraints': self.goal_constraints
        }
        return context
    
    def _retrieve_memory_context(self, prompt: str) -> List[Dict[str, Any]]:
        """Get relevant context from memory."""
        # Get recent interactions from short-term memory
        recent = self.short_term_memory[-self.num_history_responses:] if self.add_history_to_messages else []
        
        # Search long-term memory if available
        long_term = []
        if self.long_term_memory:
            # Simple keyword matching for now
            long_term = [
                item for item in self.long_term_memory['interactions']
                if any(word in item.get('text', '') for word in prompt.split())
            ]
        
        return recent + long_term
    
    def _prepare_tools(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare available tools based on context."""
        if not self.show_tool_calls:
            return {}
            
        available = {}
        for name, tool in self.available_tools.items():
            if len(self.tool_calls_history) < (self.tool_call_limit or float('inf')):
                available[name] = tool
        return available
    
    def _get_knowledge_references(self, prompt: str) -> List[Dict[str, Any]]:
        """Get relevant knowledge references."""
        if not (self.knowledge_base and self.add_references):
            return []
            
        # Check cache first
        cache_key = prompt[:50]  # Use first 50 chars as cache key
        if cache_key in self.knowledge_cache:
            return self.knowledge_cache[cache_key]
            
        # Search knowledge base
        refs = self.knowledge_base.search(prompt) if hasattr(self.knowledge_base, 'search') else []
        self.knowledge_cache[cache_key] = refs
        return refs
    
    def _generate_response(self, prompt: str, context: Dict[str, Any],
                          memory_context: List[Dict[str, Any]], tools: Dict[str, Any],
                          knowledge_refs: List[Dict[str, Any]], **kwargs) -> Any:
        """Generate response using the model."""
        # Combine all context
        full_context = {
            **context,
            'memory': memory_context,
            'tools': list(tools.keys()),
            'knowledge': knowledge_refs
        }
        
        # Generate response
        response = self.model.generate(
            prompt=prompt,
            context=full_context,
            stream=self.stream,
            **kwargs
        )
        
        return response
    
    def _update_goals(self, prompt: str, response: Any) -> None:
        """Update goal system based on interaction."""
        if not self.current_goal:
            return
            
        # Simple progress tracking
        self.goal_metrics['current_progress'] += 0.1
        if self.goal_metrics['current_progress'] >= 1.0:
            self.goal_metrics['completed_goals'] += 1
            self.goal_history.append({
                'goal': self.current_goal,
                'status': 'completed',
                'timestamp': datetime.now().isoformat()
            })
            
            # Get next goal from stack if available
            if self.goal_stack:
                self.current_goal = self.goal_stack.pop(0)
                self.goal_metrics['current_progress'] = 0.0
    
    def _store_interaction(self, prompt: str, response: Any, context: Dict[str, Any]) -> None:
        """Store interaction in memory systems."""
        interaction = {
            'timestamp': datetime.now().isoformat(),
            'prompt': prompt,
            'response': response,
            'context': context
        }
        
        # Update short-term memory
        self.short_term_memory.append(interaction)
        if len(self.short_term_memory) > self.memory_window_size:
            self.short_term_memory.pop(0)
        
        # Update long-term memory
        if self.long_term_memory:
            self.long_term_memory['interactions'].append(interaction)
    
    def _update_mental_state(self, prompt: str) -> None:
        """Update the agent's mental state based on the prompt."""
        self.mental_state["datetime"] = datetime.now().isoformat()
        self.mental_state["attention"] = prompt
        
        if self.memory:
            # Update memory context if memory system exists
            self.mental_state["memory_context"] = self._retrieve_relevant_memory(prompt)
    
    def _process_prompt(self, prompt: str, **kwargs) -> Any:
        """Process the prompt using the model and any additional tools."""
        # If knowledge base exists, augment prompt with relevant knowledge
        if self.knowledge_base:
            context = self.knowledge_base.search(prompt)
            prompt = self._augment_prompt_with_context(prompt, context)
        
        # Generate response using the model
        response = self.model.generate(prompt, **kwargs)
        
        # If tools are available, try to use them based on the response
        if self.tools:
            response = self._apply_tools(response)
        
        return response
    
    def _retrieve_relevant_memory(self, prompt: str) -> List[Dict[str, Any]]:
        """Retrieve relevant memories based on the prompt."""
        if not self.memory:
            return []
        return self.memory.search(prompt)
    
    def _augment_prompt_with_context(self, prompt: str, context: List[str]) -> str:
        """Augment the prompt with retrieved context."""
        if not context:
            return prompt
        context_str = "\n".join(context)
        return f"Context:\n{context_str}\n\nPrompt: {prompt}"
    
    def _apply_tools(self, response: Any) -> Any:
        """Apply available tools based on the response."""
        for tool in self.tools:
            if tool.should_apply(response):
                response = tool.apply(response)
        return response
