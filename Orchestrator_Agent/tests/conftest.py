import pytest
from models.task import Task, SubTask, TaskStatus, TaskPriority
from models.agent_profile import AgentProfile, AgentCapability, AgentStatus
from orchestrator.task_decomposer import TaskDecomposer
from orchestrator.agent_registry import AgentRegistry
from orchestrator.agent_negotiator import AgentNegotiator
from orchestrator.agent_executor import AgentExecutor
from orchestrator.result_aggregator import ResultAggregator
from orchestrator.payment_handler import PaymentHandler
from utils.cost_optimizer import CostOptimizer
from utils.cache import Cache
from utils.did_resolver import DIDResolver


@pytest.fixture
def sample_task():
    """Create a sample task for testing"""
    task = Task(
        title="Research and Analysis Task",
        description="Complete research and analysis workflow",
        objective="Gather data, analyze it, and generate report",
        required_capabilities=["web-research", "data-analysis", "text-generation"],
        max_budget=100.0,
        priority=TaskPriority.HIGH
    )
    return task


@pytest.fixture
def sample_subtask():
    """Create a sample subtask"""
    subtask = SubTask(
        description="Perform web research on topic",
        required_capabilities=["web-research"],
        estimated_duration=60,
        max_budget=25.0
    )
    return subtask


@pytest.fixture
def orchestrator_did():
    """Sample orchestrator DID"""
    return "did:bindu:orchestrator:test:001"


@pytest.fixture
def sample_agents():
    """Create sample agents for testing"""
    agents = []
    
    # Research Agent
    research_agent = AgentProfile(
        did="did:bindu:agent:research:test",
        name="Test Research Agent",
        description="Research capability",
        owner="test@bindu.io",
        endpoint_url="http://localhost:3001"
    )
    research_agent.add_capability(AgentCapability(
        name="web-research",
        description="Web research capability",
        cost_per_call=10.0,
        success_rate=0.95,
        avg_execution_time=60
    ))
    agents.append(research_agent)
    
    # Analysis Agent
    analysis_agent = AgentProfile(
        did="did:bindu:agent:analysis:test",
        name="Test Analysis Agent",
        description="Analysis capability",
        owner="test@bindu.io",
        endpoint_url="http://localhost:3002"
    )
    analysis_agent.add_capability(AgentCapability(
        name="data-analysis",
        description="Data analysis capability",
        cost_per_call=15.0,
        success_rate=0.92,
        avg_execution_time=90
    ))
    agents.append(analysis_agent)
    
    # Generation Agent
    generation_agent = AgentProfile(
        did="did:bindu:agent:generation:test",
        name="Test Generation Agent",
        description="Content generation capability",
        owner="test@bindu.io",
        endpoint_url="http://localhost:3003"
    )
    generation_agent.add_capability(AgentCapability(
        name="text-generation",
        description="Text generation capability",
        cost_per_call=8.0,
        success_rate=0.88,
        avg_execution_time=120
    ))
    agents.append(generation_agent)
    
    return agents


@pytest.fixture
def task_decomposer():
    """Create TaskDecomposer instance"""
    return TaskDecomposer()


@pytest.fixture
def agent_registry():
    """Create AgentRegistry instance"""
    return AgentRegistry()


@pytest.fixture
def agent_negotiator(orchestrator_did):
    """Create AgentNegotiator instance"""
    return AgentNegotiator(orchestrator_did)


@pytest.fixture
def agent_executor(orchestrator_did):
    """Create AgentExecutor instance"""
    return AgentExecutor(orchestrator_did)


@pytest.fixture
def result_aggregator():
    """Create ResultAggregator instance"""
    return ResultAggregator()


@pytest.fixture
def payment_handler(orchestrator_did):
    """Create PaymentHandler instance"""
    return PaymentHandler(orchestrator_did)


@pytest.fixture
def cost_optimizer():
    """Create CostOptimizer instance"""
    return CostOptimizer()


@pytest.fixture
def cache():
    """Create Cache instance"""
    return Cache(default_ttl=300)


@pytest.fixture
def did_resolver():
    """Create DIDResolver instance"""
    return DIDResolver()


@pytest.fixture(autouse=True)
def cleanup():
    """Cleanup after each test"""
    yield
    # Cleanup code here if needed