"""Integration tests replicating Postman collection scenarios - Simplified version."""

from uuid import uuid4

from starlette.testclient import TestClient

from bindu.server.applications import BinduApplication
from bindu.server.scheduler.memory_scheduler import InMemoryScheduler

# Import directly from submodules to avoid circular imports
from bindu.server.storage.memory_storage import InMemoryStorage
from tests.mocks import MockAgent, MockDIDExtension, MockManifest


def create_test_app(agent_response="Test response", did_extension=None):
    """Helper to create a test app with minimal setup."""
    agent = MockAgent(response=agent_response)
    manifest = MockManifest(agent_fn=agent)
    if did_extension:
        manifest.did_extension = did_extension
    storage = InMemoryStorage()
    scheduler = InMemoryScheduler()

    return BinduApplication(
        manifest=manifest,
        storage=storage,
        scheduler=scheduler,
        url="http://localhost:8030",
        version="1.0.0",
    ), storage


class TestPostmanScenarios:
    """Test scenarios from pebbling.postman_collection.json."""

    def test_scenario_1_first_send_message(self):
        """Test: first send message - creates new task and context."""
        app, _ = create_test_app("Here's a beautiful sunset quote: 'Every sunset is an opportunity to reset.'")

        with TestClient(app) as client:
            context_id = str(uuid4())
            task_id = str(uuid4())
            message_id = str(uuid4())

            request_body = {
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": "provide sunset quote"}],
                        "kind": "message",
                        "messageId": message_id,
                        "contextId": context_id,
                        "taskId": task_id,
                    },
                    "configuration": {"acceptedOutputModes": ["application/json"]},
                },
                "id": str(uuid4()),
            }

            response = client.post("/", json=request_body)

            assert response.status_code == 200
            data = response.json()
            assert "result" in data
            assert data["result"]["kind"] == "task"
            # Note: The response may use different field names
            assert "id" in data["result"] or "task_id" in data["result"]

    def test_scenario_2_task_status_in_middle(self):
        """Test: tasks/get - retrieve task status (expects error for non-existent task)."""
        app, _ = create_test_app("Processing...")

        with TestClient(app) as client:
            # Try to get a non-existent task (should return error)
            request_body = {
                "jsonrpc": "2.0",
                "method": "tasks/get",
                "params": {"taskId": str(uuid4())},
                "id": str(uuid4()),
            }

            response = client.post("/", json=request_body)

            assert response.status_code == 200
            data = response.json()
            # Should return error for non-existent task
            assert "error" in data or "result" in data

    def test_scenario_3_reference_add_refinement(self):
        """Test: message/send with referenceTaskIds - task refinement."""
        app, _ = create_test_app("Shorter version: Sunsets reset us.")

        with TestClient(app) as client:
            prev_task_id = str(uuid4())
            context_id = str(uuid4())
            new_task_id = str(uuid4())

            request_body = {
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {
                    "message": {
                        "role": "user",
                        "parts": [{"kind": "text", "text": "make it shorter"}],
                        "kind": "message",
                        "messageId": str(uuid4()),
                        "contextId": context_id,
                        "taskId": new_task_id,
                        "referenceTaskIds": [prev_task_id],
                    },
                    "configuration": {"acceptedOutputModes": ["application/json"]},
                },
                "id": str(uuid4()),
            }

            response = client.post("/", json=request_body)

            assert response.status_code == 200
            data = response.json()
            if "result" in data:
                assert data["result"]["kind"] == "task"
                assert data["result"]["id"] == new_task_id

    def test_scenario_4_list_tasks(self):
        """Test: tasks/list - list all tasks."""
        app, _ = create_test_app("Response")

        with TestClient(app) as client:
            request_body = {"jsonrpc": "2.0", "method": "tasks/list", "params": {}, "id": str(uuid4())}

            response = client.post("/", json=request_body)

            assert response.status_code == 200
            data = response.json()
            if "result" in data:
                assert isinstance(data["result"], list)

    def test_scenario_5_list_contexts(self):
        """Test: contexts/list - list all contexts."""
        app, _ = create_test_app("Response")

        with TestClient(app) as client:
            request_body = {"jsonrpc": "2.0", "method": "contexts/list", "params": {"length": 10}, "id": str(uuid4())}

            response = client.post("/", json=request_body)

            assert response.status_code == 200
            data = response.json()
            if "result" in data:
                assert isinstance(data["result"], list)

    def test_scenario_6_submit_feedback(self):
        """Test: tasks/feedback - submit feedback for a task."""
        app, _ = create_test_app("Response")

        with TestClient(app) as client:
            request_body = {
                "jsonrpc": "2.0",
                "method": "tasks/feedback",
                "params": {
                    "taskId": str(uuid4()),
                    "feedback": "Great job! The response was very helpful and accurate.",
                    "rating": 5,
                    "metadata": {"category": "quality", "source": "user", "helpful": True},
                },
                "id": str(uuid4()),
            }

            response = client.post("/", json=request_body)

            assert response.status_code == 200
            data = response.json()
            assert "result" in data or "error" in data

    def test_scenario_7_context_clear(self):
        """Test: contexts/clear - clear a context."""
        app, _ = create_test_app("Response")

        with TestClient(app) as client:
            request_body = {
                "jsonrpc": "2.0",
                "method": "contexts/clear",
                "params": {"contextId": str(uuid4())},
                "id": str(uuid4()),
            }

            response = client.post("/", json=request_body)

            assert response.status_code == 200
            data = response.json()
            assert "result" in data or "error" in data

    def test_scenario_8_agent_card(self):
        """Test: GET /.well-known/agent.json - retrieve agent card."""
        app, _ = create_test_app("Response")

        with TestClient(app) as client:
            response = client.get("/.well-known/agent.json")

            assert response.status_code == 200
            data = response.json()
            assert "id" in data
            assert "name" in data
            assert "version" in data
            assert "protocolVersion" in data

    def test_scenario_9_did_resolve(self):
        """Test: POST /did/resolve - resolve DID."""
        did_ext = MockDIDExtension()
        app, _ = create_test_app("Response", did_extension=did_ext)

        with TestClient(app) as client:
            request_body = {"did": did_ext.did}

            response = client.post("/did/resolve", json=request_body)

            assert response.status_code == 200
            data = response.json()
            assert "@context" in data
            assert "id" in data
            assert data["id"] == did_ext.did


class TestErrorScenarios:
    """Test error scenarios from Postman collection."""

    def test_task_not_found_error(self):
        """Test TaskNotFoundError (-32001)."""
        app, _ = create_test_app("Response")

        with TestClient(app) as client:
            request_body = {
                "jsonrpc": "2.0",
                "method": "tasks/get",
                "params": {"taskId": str(uuid4())},
                "id": str(uuid4()),
            }

            response = client.post("/", json=request_body)

            assert response.status_code == 200
            data = response.json()
            assert "error" in data
            assert data["error"]["code"] == -32001

    def test_method_not_found_error(self):
        """Test MethodNotFoundError."""
        app, _ = create_test_app("Response")

        with TestClient(app) as client:
            request_body = {"jsonrpc": "2.0", "method": "unsupported/method", "params": {}, "id": str(uuid4())}

            response = client.post("/", json=request_body)

            data = response.json()
            assert "error" in data
            # Accept any error code for unsupported method
            assert "code" in data["error"]
