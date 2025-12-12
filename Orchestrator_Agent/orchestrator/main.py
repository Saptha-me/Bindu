import asyncio
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Import orchestrator components
from .task_decomposer import TaskDecomposer
from .agent_registry import AgentRegistry
from .agent_negotiator import AgentNegotiator
from .agent_executor import AgentExecutor
from .result_aggregator import ResultAggregator
from .payment_handler import PaymentHandler

from models.task import Task, TaskStatus
from models.agent_profile import AgentProfile, AgentCapability
from utils.logger import get_logger, configure_logging
from utils.cost_optimizer import CostOptimizer
from utils.cache import Cache


configure_logging()
logger = get_logger(__name__)


app = FastAPI(
    title="Bindu Orchestrator Engine",
    description="Multi-Agent Task Orchestration System",
    version="1.0.0",
)


task_decomposer: TaskDecomposer = None
agent_registry: AgentRegistry = None
agent_negotiator: AgentNegotiator = None
agent_executor: AgentExecutor = None
result_aggregator: ResultAggregator = None
payment_handler: PaymentHandler = None
cost_optimizer: CostOptimizer = None
cache: Cache = None
orchestrator_did: str = "did:bindu:orchestrator:main:001"


class TaskRequest(BaseModel):
    """Task submission request"""
    title: str
    description: str
    required_capabilities: List[str]
    max_budget: float
    deadline_hours: int = 24

class TaskResponse(BaseModel):
    """Task submission response"""
    task_id: str
    status: str
    message: str
    created_at: str

class ExecutionRequest(BaseModel):
    """Task execution request"""
    task_id: str

class ExecutionResponse(BaseModel):
    """Task execution response"""
    task_id: str
    status: str
    subtasks_completed: int
    agents_engaged: int
    payments_settled: int
    total_cost: float
    result_summary: str


@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator components on startup"""
    global task_decomposer, agent_registry, agent_negotiator, agent_executor
    global result_aggregator, payment_handler, cost_optimizer, cache
    
    logger.info("🚀 Starting Bindu Orchestrator Engine...")
    
    try:
        # Initialize components
        cache = Cache(default_ttl=3600)
        task_decomposer = TaskDecomposer()
        agent_registry = AgentRegistry()
        agent_negotiator = AgentNegotiator(orchestrator_did)
        agent_executor = AgentExecutor(orchestrator_did)
        result_aggregator = ResultAggregator()
        payment_handler = PaymentHandler(orchestrator_did)
        cost_optimizer = CostOptimizer()
        
        # Register default agents
        logger.info("📋 Registering default agents...")
        _register_default_agents()
        
        logger.info("✅ Orchestrator initialization complete!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down Bindu Orchestrator Engine...")
    if cache:
        cache.clear()
    logger.info("✅ Shutdown complete!")


@app.get("/health")
async def health_check():
    """Basic health check endpoint"""
    return {
        "status": "healthy",
        "service": "bindu-orchestrator",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/status")
async def status():
    """Detailed status endpoint"""
    return {
        "orchestrator_did": orchestrator_did,
        "status": "running",
        "agents_registered": agent_registry.get_all_agents().__len__() if agent_registry else 0,
        "cache_size": cache.get_size() if cache else 0,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint"""
    return {
        "agents_total": agent_registry.get_all_agents().__len__() if agent_registry else 0,
        "cache_entries": cache.get_size() if cache else 0,
        "orchestrator_id": orchestrator_did,
        "uptime_seconds": 0  # Add real uptime tracking
    }


@app.post("/tasks/submit", response_model=TaskResponse)
async def submit_task(request: TaskRequest):

    logger.info(f"📥 Task submission: {request.title}")
    
    try:
        # Create task
        task = Task(
            title=request.title,
            description=request.description,
            required_capabilities=request.required_capabilities,
            max_budget=request.max_budget
        )
        
        logger.info(f"✅ Task created: {task.id}")
        
        return TaskResponse(
            task_id=task.id,
            status="created",
            message="Task submitted successfully",
            created_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        logger.error(f"❌ Task submission failed: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/tasks/execute", response_model=ExecutionResponse)
async def execute_task(request: ExecutionRequest):

    logger.info(f"🎬 Starting execution workflow for task: {request.task_id}")
    
    try:
        # STEP 1: DECOMPOSE TASK
        logger.info("📋 Step 1: Decomposing task...")
        # In real implementation, fetch task from DB
        sample_task = Task(
            title="Test Task",
            description="Test execution",
            required_capabilities=["web-research", "data-analysis"],
            max_budget=100.0
        )
        
        subtasks = task_decomposer.decompose(sample_task)
        logger.info(f"✅ Decomposed into {len(subtasks)} subtasks")
        
        # STEP 2: DISCOVER AGENTS
        logger.info("🔍 Step 2: Discovering agents...")
        available_agents = agent_registry.get_all_agents()
        logger.info(f"✅ Found {len(available_agents)} available agents")
        
        # STEP 3: NEGOTIATE WITH AGENTS
        logger.info("💬 Step 3: Negotiating with agents...")
        negotiations = {}
        for subtask in subtasks:
            if subtask.required_capabilities:
                capability = subtask.required_capabilities[0]
                agent = agent_registry.find_cheapest_agent(available_agents, capability)
                
                if agent:
                    negotiation = agent_negotiator.initiate_negotiation(
                        agent, subtask, subtask.max_budget
                    )
                    quote = agent_negotiator.request_quote(
                        negotiation, agent, capability
                    )
                    
                    if quote and agent_negotiator.process_quote(negotiation.id, quote):
                        agent_negotiator.accept_quote(negotiation.id)
                        negotiations[subtask.id] = (agent, negotiation)
        
        logger.info(f"✅ Negotiated with {len(negotiations)} agents")
        
        # STEP 4: EXECUTE TASKS
        logger.info("⚙️ Step 4: Executing tasks...")
        execution_results = {}
        for subtask in subtasks:
            if subtask.id in negotiations:
                agent, negotiation = negotiations[subtask.id]
                try:
                    result = agent_executor.execute_subtask(agent.did, subtask)
                    execution_results[subtask.id] = result
                except Exception as e:
                    logger.warning(f"⚠️ Execution failed for {subtask.id}: {str(e)}")
        
        logger.info(f"✅ Executed {len(execution_results)} tasks")
        
        # STEP 5: AGGREGATE RESULTS
        logger.info("📊 Step 5: Aggregating results...")
        aggregated = result_aggregator.aggregate(sample_task, execution_results)
        logger.info(f"✅ Results aggregated: {aggregated.summary}")
        
        # STEP 6: SETTLE PAYMENTS
        logger.info("💳 Step 6: Processing payments...")
        total_payment = 0.0
        payment_count = 0
        
        for subtask in subtasks:
            if subtask.id in negotiations:
                agent, negotiation = negotiations[subtask.id]
                cost = agent.estimate_cost(subtask.required_capabilities)
                
                transaction = payment_handler.create_payment(agent.did, cost)
                result = payment_handler.settle_payment(transaction.id)
                
                if result:
                    payment_count += 1
                    total_payment += cost
        
        logger.info(f"✅ Processed {payment_count} payments (${total_payment:.2f} total)")
        
        # SUCCESS
        logger.info(f"🎉 Execution workflow complete for task: {request.task_id}")
        
        return ExecutionResponse(
            task_id=request.task_id,
            status="completed",
            subtasks_completed=len(execution_results),
            agents_engaged=len(negotiations),
            payments_settled=payment_count,
            total_cost=total_payment,
            result_summary=aggregated.summary if aggregated else "No results"
        )
        
    except Exception as e:
        logger.error(f"❌ Execution failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents")
async def list_agents():
    """List all registered agents"""
    agents = agent_registry.get_all_agents() if agent_registry else []
    return {
        "total": len(agents),
        "agents": [
            {
                "did": agent.did,
                "name": agent.name,
                "capabilities": [cap.name for cap in agent.capabilities],
                "endpoint": agent.endpoint
            }
            for agent in agents
        ]
    }

@app.get("/agents/search")
async def search_agents(capability: str):
    """Search agents by capability"""
    agents = agent_registry.find_agents_by_capability(capability) if agent_registry else []
    return {
        "capability": capability,
        "agents_found": len(agents),
        "agents": [
            {
                "did": agent.did,
                "name": agent.name,
                "endpoint": agent.endpoint
            }
            for agent in agents
        ]
    }


def _register_default_agents():
    """Register default agents for orchestrator"""
    
    agents_config = [
        {
            "did": "did:bindu:agent:research:001",
            "name": "Research Agent",
            "description": "Web research and information gathering",
            "endpoint": "http://research-agent:3001",
            "capabilities": [
                {"name": "web-research", "cost": 5.0, "success_rate": 0.98, "time": 60}
            ]
        },
        {
            "did": "did:bindu:agent:analysis:001",
            "name": "Analysis Agent",
            "description": "Data analysis and insights generation",
            "endpoint": "http://analysis-agent:3002",
            "capabilities": [
                {"name": "data-analysis", "cost": 10.0, "success_rate": 0.96, "time": 90}
            ]
        },
        {
            "did": "did:bindu:agent:generation:001",
            "name": "Generation Agent",
            "description": "Content and report generation",
            "endpoint": "http://generation-agent:3003",
            "capabilities": [
                {"name": "text-generation", "cost": 8.0, "success_rate": 0.94, "time": 120}
            ]
        },
        {
            "did": "did:bindu:agent:verification:001",
            "name": "Verification Agent",
            "description": "Quality verification and accuracy checking",
            "endpoint": "http://verification-agent:3004",
            "capabilities": [
                {"name": "quality-check", "cost": 7.0, "success_rate": 0.99, "time": 45}
            ]
        }
    ]
    
    for agent_config in agents_config:
        agent = AgentProfile(
            did=agent_config["did"],
            name=agent_config["name"],
            description=agent_config["description"],
            owner="bindu-team@bindu.io",
            endpoint_url=agent_config["endpoint"]
        )
        
        for cap_config in agent_config["capabilities"]:
            capability = AgentCapability(
                name=cap_config["name"],
                description=f"{cap_config['name']} capability",
                cost_per_call=cap_config["cost"],
                success_rate=cap_config["success_rate"],
                avg_execution_time=cap_config["time"]
            )
            agent.add_capability(capability)
        
        agent_registry.register_agent(agent)
        logger.info(f"✅ Registered agent: {agent.name}")


if __name__ == "__main__":
    logger.info("🚀 Starting Bindu Orchestrator...")
    
    uvicorn.run(
        "orchestrator.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Set to True for development
        log_level="info"
    )