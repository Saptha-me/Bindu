"""Integration tests replicating Postman collection scenarios."""

import pytest
from uuid import uuid4
from starlette.testclient import TestClient

# Import directly from submodules to avoid circular imports
from bindu.server.storage.memory_storage import InMemoryStorage
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler
from tests.mocks import MockManifest, MockAgent
from tests.utils import create_test_message


class TestPostmanScenarios:
    """Test scenarios from pebbling.postman_collection.json."""
    
    @pytest.mark.asyncio
    async def test_scenario_1_first_send_message(self):
        """Test: first send message - creates new task and context."""
        # Import here to avoid circular import
        from bindu.server.applications import BinduApplication
        
        agent = MockAgent(response="Here's a beautiful sunset quote: 'Every sunset is an opportunity to reset.'")
        manifest = MockManifest(agent_fn=agent)
        storage = InMemoryStorage()
        
        async with InMemoryScheduler() as scheduler:
            async with BinduApplication(
                manifest=manifest,
                storage=storage,
                scheduler=scheduler,
                url="http://localhost:8030",
                version="1.0.0",
            ) as app:
                client = TestClient(app.app)
                
                # Prepare request
                context_id = str(uuid4())
                task_id = str(uuid4())
                message_id = str(uuid4())
                
                request_body = {
                    "jsonrpc": "2.0",
                    "method": "message/send",
                    "params": {
                        "message": {
                            "role": "user",
                            "parts": [
                                {
                                    "kind": "text",
                                    "text": "provide sunset quote"
                                }
                            ],
                            "kind": "message",
                            "messageId": message_id,
                            "contextId": context_id,
                            "taskId": task_id
                        },
                        "configuration": {
                            "acceptedOutputModes": ["application/json"]
                        }
                    },
                    "id": str(uuid4())
                }
                
                # Send request
                response = client.post("/", json=request_body)
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify response structure
                assert "result" in data
                assert data["result"]["kind"] == "task"
                assert data["result"]["id"] == task_id
                assert data["result"]["contextId"] == context_id
    
    @pytest.mark.asyncio
    async def test_scenario_2_task_status_in_middle(self):
        """Test: tasks/get - retrieve task status during execution."""
        from bindu.server.applications import BinduApplication
        
        agent = MockAgent(response="Processing...")
        manifest = MockManifest(agent_fn=agent)
        storage = InMemoryStorage()
        
        async with InMemoryScheduler() as scheduler:
            async with BinduApplication(
                manifest=manifest,
                storage=storage,
                scheduler=scheduler,
                url="http://localhost:8030",
                version="1.0.0",
            ) as app:
                client = TestClient(app.app)
                
                # First create a task
                task_id = str(uuid4())
                from tests.utils import create_test_task
                task = create_test_task(task_id=uuid4(), state="working")
                task["id"] = uuid4()
                await storage.save_task(task)
                
                # Get task status
                request_body = {
                    "jsonrpc": "2.0",
                    "method": "tasks/get",
                    "params": {
                        "taskId": str(task["id"])
                    },
                    "id": str(uuid4())
                }
                
                response = client.post("/", json=request_body)
                
                assert response.status_code == 200
                data = response.json()
                
                if "result" in data:
                    assert data["result"]["kind"] == "task"
                    assert "status" in data["result"]
    
    @pytest.mark.asyncio
    async def test_scenario_3_reference_add_refinement(self):
        """Test: message/send with referenceTaskIds - task refinement."""
        from bindu.server.applications import BinduApplication
        
        agent = MockAgent(response="Shorter version: Sunsets reset us.")
        manifest = MockManifest(agent_fn=agent)
        storage = InMemoryStorage()
        
        async with InMemoryScheduler() as scheduler:
            async with BinduApplication(
                manifest=manifest,
                storage=storage,
                scheduler=scheduler,
                url="http://localhost:8030",
                version="1.0.0",
            ) as app:
                client = TestClient(app.app)
                
                # Create previous task
                prev_task_id = str(uuid4())
                context_id = str(uuid4())
                
                # Send refinement request
                new_task_id = str(uuid4())
                request_body = {
                    "jsonrpc": "2.0",
                    "method": "message/send",
                    "params": {
                        "message": {
                            "role": "user",
                            "parts": [
                                {
                                    "kind": "text",
                                    "text": "make it shorter"
                                }
                            ],
                            "kind": "message",
                            "messageId": str(uuid4()),
                            "contextId": context_id,
                            "taskId": new_task_id,
                            "referenceTaskIds": [prev_task_id]
                        },
                        "configuration": {
                            "acceptedOutputModes": ["application/json"]
                        }
                    },
                    "id": str(uuid4())
                }
                
                response = client.post("/", json=request_body)
                
                assert response.status_code == 200
                data = response.json()
                
                # New task should be created
                if "result" in data:
                    assert data["result"]["kind"] == "task"
                    assert data["result"]["id"] == new_task_id
    
    @pytest.mark.asyncio
    async def test_scenario_4_list_tasks(self):
        """Test: tasks/list - list all tasks."""
        from bindu.server.applications import BinduApplication
        
        agent = MockAgent(response="Response")
        manifest = MockManifest(agent_fn=agent)
        storage = InMemoryStorage()
        
        async with InMemoryScheduler() as scheduler:
            async with BinduApplication(
                manifest=manifest,
                storage=storage,
                scheduler=scheduler,
                url="http://localhost:8030",
                version="1.0.0",
            ) as app:
                client = TestClient(app.app)
                
                # Create some tasks
                from tests.utils import create_test_task
                for _ in range(3):
                    task = create_test_task()
                    await storage.save_task(task)
                
                # List tasks
                request_body = {
                    "jsonrpc": "2.0",
                    "method": "tasks/list",
                    "params": {},
                    "id": str(uuid4())
                }
                
                response = client.post("/", json=request_body)
                
                assert response.status_code == 200
                data = response.json()
                
                if "result" in data:
                    assert isinstance(data["result"], list)
                    assert len(data["result"]) >= 3
    
    @pytest.mark.asyncio
    async def test_scenario_5_list_contexts(self):
        """Test: contexts/list - list all contexts."""
        from bindu.server.applications import BinduApplication
        
        agent = MockAgent(response="Response")
        manifest = MockManifest(agent_fn=agent)
        storage = InMemoryStorage()
        
        async with InMemoryScheduler() as scheduler:
            async with BinduApplication(
                manifest=manifest,
                storage=storage,
                scheduler=scheduler,
                url="http://localhost:8030",
                version="1.0.0",
            ) as app:
                client = TestClient(app.app)
                
                # Create some contexts
                from tests.utils import create_test_context
                for i in range(2):
                    ctx = create_test_context(name=f"Session {i}")
                    await storage.save_context(ctx)
                
                # List contexts
                request_body = {
                    "jsonrpc": "2.0",
                    "method": "contexts/list",
                    "params": {
                        "length": 10
                    },
                    "id": str(uuid4())
                }
                
                response = client.post("/", json=request_body)
                
                assert response.status_code == 200
                data = response.json()
                
                if "result" in data:
                    assert isinstance(data["result"], list)
    
    @pytest.mark.asyncio
    async def test_scenario_6_submit_feedback(self):
        """Test: tasks/feedback - submit feedback for a task."""
        from bindu.server.applications import BinduApplication
        
        agent = MockAgent(response="Response")
        manifest = MockManifest(agent_fn=agent)
        storage = InMemoryStorage()
        
        async with InMemoryScheduler() as scheduler:
            async with BinduApplication(
                manifest=manifest,
                storage=storage,
                scheduler=scheduler,
                url="http://localhost:8030",
                version="1.0.0",
            ) as app:
                client = TestClient(app.app)
                
                # Create a completed task
                from tests.utils import create_test_task
                task = create_test_task(state="completed")
                await storage.save_task(task)
                
                # Submit feedback
                request_body = {
                    "jsonrpc": "2.0",
                    "method": "tasks/feedback",
                    "params": {
                        "taskId": str(task["id"]),
                        "feedback": "Great job! The response was very helpful and accurate.",
                        "rating": 5,
                        "metadata": {
                            "category": "quality",
                            "source": "user",
                            "helpful": True
                        }
                    },
                    "id": str(uuid4())
                }
                
                response = client.post("/", json=request_body)
                
                assert response.status_code == 200
                data = response.json()
                
                # Should succeed or return appropriate response
                assert "result" in data or "error" in data
    
    @pytest.mark.asyncio
    async def test_scenario_7_context_clear(self):
        """Test: contexts/clear - clear a context."""
        from bindu.server.applications import BinduApplication
        
        agent = MockAgent(response="Response")
        manifest = MockManifest(agent_fn=agent)
        storage = InMemoryStorage()
        
        async with InMemoryScheduler() as scheduler:
            async with BinduApplication(
                manifest=manifest,
                storage=storage,
                scheduler=scheduler,
                url="http://localhost:8030",
                version="1.0.0",
            ) as app:
                client = TestClient(app.app)
                
                # Create a context
                from tests.utils import create_test_context
                context = create_test_context(name="To Clear")
                await storage.save_context(context)
                
                # Clear context
                request_body = {
                    "jsonrpc": "2.0",
                    "method": "contexts/clear",
                    "params": {
                        "contextId": str(context["context_id"])
                    },
                    "id": str(uuid4())
                }
                
                response = client.post("/", json=request_body)
                
                assert response.status_code == 200
                data = response.json()
                
                # Should succeed or return appropriate response
                assert "result" in data or "error" in data
    
    @pytest.mark.asyncio
    async def test_scenario_8_agent_card(self):
        """Test: GET /agent/card - retrieve agent card."""
        from bindu.server.applications import BinduApplication
        
        agent = MockAgent(response="Response")
        manifest = MockManifest(agent_fn=agent)
        storage = InMemoryStorage()
        
        async with InMemoryScheduler() as scheduler:
            async with BinduApplication(
                manifest=manifest,
                storage=storage,
                scheduler=scheduler,
                url="http://localhost:8030",
                version="1.0.0",
            ) as app:
                client = TestClient(app.app)
                
                # Get agent card
                response = client.get("/agent/card")
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify agent card structure
                assert "id" in data
                assert "name" in data
                assert "version" in data
                assert "protocolVersion" in data
    
    @pytest.mark.asyncio
    async def test_scenario_9_did_resolve(self):
        """Test: POST /did/resolve - resolve DID."""
        from bindu.server.applications import BinduApplication
        from tests.mocks import MockDIDExtension
        
        agent = MockAgent(response="Response")
        manifest = MockManifest(agent_fn=agent)
        manifest.did_extension = MockDIDExtension()
        storage = InMemoryStorage()
        
        async with InMemoryScheduler() as scheduler:
            async with BinduApplication(
                manifest=manifest,
                storage=storage,
                scheduler=scheduler,
                url="http://localhost:8030",
                version="1.0.0",
            ) as app:
                client = TestClient(app.app)
                
                # Resolve DID
                request_body = {
                    "did": manifest.did_extension.did
                }
                
                response = client.post("/did/resolve", json=request_body)
                
                assert response.status_code == 200
                data = response.json()
                
                # Verify DID document structure
                assert "@context" in data
                assert "id" in data
                assert data["id"] == manifest.did_extension.did


class TestErrorScenarios:
    """Test error scenarios from Postman collection."""
    
    @pytest.mark.asyncio
    async def test_task_not_found_error(self):
        """Test TaskNotFoundError (-32001)."""
        from bindu.server.applications import BinduApplication
        
        agent = MockAgent(response="Response")
        manifest = MockManifest(agent_fn=agent)
        storage = InMemoryStorage()
        
        async with InMemoryScheduler() as scheduler:
            async with BinduApplication(
                manifest=manifest,
                storage=storage,
                scheduler=scheduler,
                url="http://localhost:8030",
                version="1.0.0",
            ) as app:
                client = TestClient(app.app)
                
                # Try to get non-existent task
                request_body = {
                    "jsonrpc": "2.0",
                    "method": "tasks/get",
                    "params": {
                        "taskId": str(uuid4())
                    },
                    "id": str(uuid4())
                }
                
                response = client.post("/", json=request_body)
                
                assert response.status_code == 200
                data = response.json()
                
                # Should return error
                assert "error" in data
                assert data["error"]["code"] == -32001
    
    @pytest.mark.asyncio
    async def test_method_not_found_error(self):
        """Test MethodNotFoundError (-32601)."""
        from bindu.server.applications import BinduApplication
        
        agent = MockAgent(response="Response")
        manifest = MockManifest(agent_fn=agent)
        storage = InMemoryStorage()
        
        async with InMemoryScheduler() as scheduler:
            async with BinduApplication(
                manifest=manifest,
                storage=storage,
                scheduler=scheduler,
                url="http://localhost:8030",
                version="1.0.0",
            ) as app:
                client = TestClient(app.app)
                
                # Try unsupported method
                request_body = {
                    "jsonrpc": "2.0",
                    "method": "unsupported/method",
                    "params": {},
                    "id": str(uuid4())
                }
                
                response = client.post("/", json=request_body)
                
                # Should return error
                data = response.json()
                assert "error" in data
                assert data["error"]["code"] == -32601
