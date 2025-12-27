"""Example client demonstrating push notification usage with Bindu agents.

This example shows:
1. How to send tasks with inline webhook registration
2. How to implement a webhook receiver
3. How to handle different notification event types
"""

import asyncio
import requests
from uuid import uuid4
from fastapi import FastAPI, Request, Header, HTTPException
import uvicorn

# Configuration
AGENT_URL = "http://localhost:3773"
WEBHOOK_URL = "https://myapp.com/webhooks/task-updates"  # Your webhook endpoint
WEBHOOK_TOKEN = "secret_abc123"


# ============================================================================
# Part 1: Webhook Receiver (FastAPI)
# ============================================================================

app = FastAPI()


@app.post("/webhooks/task-updates")
async def handle_task_update(
    request: Request,
    authorization: str = Header(None)
):
    """Handle webhook notifications from Bindu agent.
    
    This endpoint receives push notifications for task state changes
    and artifact generation.
    """
    # Verify authentication token
    expected_token = f"Bearer {WEBHOOK_TOKEN}"
    if authorization != expected_token:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    # Parse event
    event = await request.json()
    
    print(f"\n{'='*60}")
    print(f"Received webhook notification:")
    print(f"Event ID: {event['event_id']}")
    print(f"Sequence: {event['sequence']}")
    print(f"Kind: {event['kind']}")
    print(f"Task ID: {event['task_id']}")
    
    # Handle different event types
    if event["kind"] == "status-update":
        state = event["status"]["state"]
        is_final = event["final"]
        
        print(f"Status: {state}")
        print(f"Final: {is_final}")
        
        if is_final:
            if state == "completed":
                print("✅ Task completed successfully!")
            elif state == "failed":
                print("❌ Task failed!")
            elif state == "canceled":
                print("⚠️  Task canceled!")
    
    elif event["kind"] == "artifact-update":
        artifact = event["artifact"]
        artifact_name = artifact.get("name", "unnamed")
        
        print(f"Artifact: {artifact_name}")
        print(f"Artifact ID: {artifact['artifact_id']}")
        
        # Process artifact data
        if "parts" in artifact:
            for part in artifact["parts"]:
                if part["kind"] == "text":
                    print(f"Text content: {part['text'][:100]}...")
                elif part["kind"] == "data":
                    print(f"Data content: {part['data']}")
    
    print(f"{'='*60}\n")
    
    return {"status": "received"}


# ============================================================================
# Part 2: Task Submission with Inline Webhook Registration
# ============================================================================

def send_task_with_webhook(message_text: str, long_running: bool = False):
    """Send a task to the agent with webhook configuration.
    
    Args:
        message_text: The message to send to the agent
        long_running: If True, webhook config will persist across server restarts
    
    Returns:
        Task ID
    """
    request_payload = {
        "jsonrpc": "2.0",
        "id": "req-1",
        "method": "messages/send",
        "params": {
            "message": {
                "message_id": str(uuid4()),
                "task_id": str(uuid4()),
                "context_id": str(uuid4()),
                "kind": "message",
                "role": "user",
                "parts": [{"kind": "text", "text": message_text}]
            },
            "configuration": {
                "accepted_output_modes": ["application/json"],
                "long_running": long_running,  # Persist webhook if True
                "push_notification_config": {
                    "id": str(uuid4()),
                    "url": WEBHOOK_URL,
                    "token": WEBHOOK_TOKEN
                }
            }
        }
    }
    
    print(f"\n{'='*60}")
    print(f"Sending task to agent...")
    print(f"Message: {message_text}")
    print(f"Long-running: {long_running}")
    print(f"Webhook URL: {WEBHOOK_URL}")
    print(f"{'='*60}\n")
    
    response = requests.post(f"{AGENT_URL}/messages/send", json=request_payload)
    response.raise_for_status()
    
    task = response.json()["result"]
    task_id = task["id"]
    
    print(f"✅ Task created: {task_id}")
    print(f"State: {task['status']['state']}")
    print(f"\nWaiting for webhook notifications...\n")
    
    return task_id


# ============================================================================
# Part 3: Alternative - RPC Webhook Registration
# ============================================================================

def register_webhook_via_rpc(task_id: str, long_running: bool = False):
    """Register webhook for an existing task using RPC method.
    
    Args:
        task_id: The task ID to register webhook for
        long_running: If True, webhook config will persist across server restarts
    """
    request_payload = {
        "jsonrpc": "2.0",
        "id": "req-2",
        "method": "tasks/pushNotification/set",
        "params": {
            "id": task_id,
            "long_running": long_running,
            "push_notification_config": {
                "id": str(uuid4()),
                "url": WEBHOOK_URL,
                "token": WEBHOOK_TOKEN
            }
        }
    }
    
    response = requests.post(f"{AGENT_URL}/rpc", json=request_payload)
    response.raise_for_status()
    
    result = response.json()["result"]
    print(f"✅ Webhook registered for task: {task_id}")
    return result


# ============================================================================
# Part 4: Usage Examples
# ============================================================================

def example_1_inline_registration():
    """Example 1: Inline webhook registration (recommended)."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Inline Webhook Registration")
    print("="*60)
    
    task_id = send_task_with_webhook(
        message_text="Process this data",
        long_running=False  # Short-lived task
    )
    
    print(f"Task submitted. Webhook notifications will arrive at {WEBHOOK_URL}")


def example_2_long_running_task():
    """Example 2: Long-running task with persistent webhook."""
    print("\n" + "="*60)
    print("EXAMPLE 2: Long-Running Task with Persistent Webhook")
    print("="*60)
    
    task_id = send_task_with_webhook(
        message_text="Process large dataset that takes hours",
        long_running=True  # Webhook survives server restarts
    )
    
    print(f"Long-running task submitted. Webhook config persisted to database.")


def example_3_rpc_registration():
    """Example 3: Separate RPC webhook registration."""
    print("\n" + "="*60)
    print("EXAMPLE 3: RPC Webhook Registration")
    print("="*60)
    
    # First create task without webhook
    request_payload = {
        "jsonrpc": "2.0",
        "id": "req-3",
        "method": "messages/send",
        "params": {
            "message": {
                "message_id": str(uuid4()),
                "task_id": str(uuid4()),
                "context_id": str(uuid4()),
                "kind": "message",
                "role": "user",
                "parts": [{"kind": "text", "text": "Process this"}]
            },
            "configuration": {
                "accepted_output_modes": ["application/json"]
            }
        }
    }
    
    response = requests.post(f"{AGENT_URL}/messages/send", json=request_payload)
    task = response.json()["result"]
    task_id = task["id"]
    
    print(f"Task created: {task_id}")
    
    # Then register webhook via RPC
    register_webhook_via_rpc(task_id, long_running=False)


# ============================================================================
# Main
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python webhook_client_example.py server    # Start webhook receiver")
        print("  python webhook_client_example.py example1  # Inline registration")
        print("  python webhook_client_example.py example2  # Long-running task")
        print("  python webhook_client_example.py example3  # RPC registration")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "server":
        print("Starting webhook receiver on http://0.0.0.0:8000")
        print(f"Webhook endpoint: http://0.0.0.0:8000/webhooks/task-updates")
        print(f"Expected token: Bearer {WEBHOOK_TOKEN}")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    
    elif command == "example1":
        example_1_inline_registration()
    
    elif command == "example2":
        example_2_long_running_task()
    
    elif command == "example3":
        example_3_rpc_registration()
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
