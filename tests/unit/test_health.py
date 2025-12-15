from types import SimpleNamespace
from starlette.testclient import TestClient
from bindu.server.applications import BinduApplication


def make_minimal_manifest():
    """
    Return a minimal manifest-like object that satisfies the
    parts of code that check manifest.capabilities and manifest.url/name.
    """
    return SimpleNamespace(
        capabilities={"extensions": []},
        url="http://localhost:3773",
        name="test_agent",
    )


def make_dummy_task_manager():
    """
    Return a minimal dummy TaskManager-like object with the attributes
    BinduApplication checks at request time.
    """
    # The app checks `task_manager is None or not task_manager.is_running`
    return SimpleNamespace(is_running=True)


def test_health_endpoint_ok():
    # Provide a minimal manifest so BinduApplication doesn't try to access attributes on None
    manifest = make_minimal_manifest()
    app = BinduApplication(manifest=manifest, debug=True)

    # Stub a minimal TaskManager so the app will accept requests in tests.
    app.task_manager = make_dummy_task_manager()

    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert isinstance(body["uptime_seconds"], (int, float))
    assert "version" in body
    assert body["ready"] is True
