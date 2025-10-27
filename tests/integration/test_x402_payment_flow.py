"""Integration tests for x402 payment flow.

Tests the complete payment flow from payment-required to payment-completed:
1. Agent with execution_cost returns payment-required
2. Client submits payment payload
3. Payment is verified with facilitator
4. Agent executes
5. Payment is settled
6. Task completes with payment-completed metadata

This follows the official A2A x402 specification.
"""

from __future__ import annotations

import json
import pytest
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from bindu.common.protocol.types import Task, TaskState
from bindu.extensions.x402.x402_agent_extension import X402AgentExtension
from bindu.penguin.manifest import AgentManifest
from bindu.server.workers.manifest_worker import ManifestWorker
from bindu.settings import app_settings
from bindu.storage.memory_storage import MemoryStorage


@pytest.fixture
def mock_facilitator_client():
    """Mock FacilitatorClient for testing."""
    with patch("bindu.server.workers.manifest_worker.FacilitatorClient") as mock:
        # Create mock instance
        instance = MagicMock()
        
        # Mock verify response (success)
        verify_response = MagicMock()
        verify_response.is_valid = True
        verify_response.invalid_reason = None
        instance.verify = AsyncMock(return_value=verify_response)
        
        # Mock settle response (success)
        settle_response = MagicMock()
        settle_response.success = True
        settle_response.error_reason = None
        settle_response.model_dump = MagicMock(return_value={
            "transactionHash": "0xabc123",
            "blockNumber": 12345,
            "network": "base-sepolia"
        })
        instance.settle = AsyncMock(return_value=settle_response)
        
        # Return instance when FacilitatorClient() is called
        mock.return_value = instance
        
        yield instance


@pytest.fixture
def storage():
    """Create in-memory storage for testing."""
    return MemoryStorage()


@pytest.fixture
def paid_agent_manifest():
    """Create a mock agent manifest with execution_cost."""
    manifest = MagicMock(spec=AgentManifest)
    manifest.name = "test-paid-agent"
    manifest.enable_system_message = True
    manifest.enable_context_based_history = False
    
    # Mock DID extension
    did_ext = MagicMock()
    did_ext.did = "did:bindu:test:paid_agent:123"
    did_ext.sign_data = MagicMock(return_value="mock_signature")
    manifest.did_extension = did_ext
    
    # Mock x402 extension
    x402_ext = MagicMock(spec=X402AgentExtension)
    x402_ext.amount_usd = 1.0
    x402_ext.token = "USDC"
    x402_ext.network = "base-sepolia"
    x402_ext.pay_to_address = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"
    x402_ext.create_payment_requirements = MagicMock(return_value=MagicMock(
        model_dump=MagicMock(return_value={
            "scheme": "exact",
            "network": "base-sepolia",
            "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
            "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
            "maxAmountRequired": "1000000",
        })
    ))
    manifest.x402_extension = x402_ext
    
    # Mock run method
    manifest.run = MagicMock(return_value="Hello! This is a paid response.")
    
    return manifest


@pytest.fixture
def free_agent_manifest():
    """Create a mock agent manifest without execution_cost."""
    manifest = MagicMock(spec=AgentManifest)
    manifest.name = "test-free-agent"
    manifest.enable_system_message = True
    manifest.enable_context_based_history = False
    
    # Mock DID extension
    did_ext = MagicMock()
    did_ext.did = "did:bindu:test:free_agent:456"
    did_ext.sign_data = MagicMock(return_value="mock_signature")
    manifest.did_extension = did_ext
    
    # No x402 extension
    manifest.x402_extension = None
    
    # Mock run method
    manifest.run = MagicMock(return_value="Hello! This is a free response.")
    
    return manifest


@pytest.mark.asyncio
@pytest.mark.x402
async def test_payment_verification_success(
    storage, paid_agent_manifest, mock_facilitator_client
):
    """Test successful payment verification and execution.
    
    Flow:
    1. Create task with payment-required metadata (from Phase 1)
    2. Submit payment payload
    3. Verify payment is verified
    4. Agent executes
    5. Payment is settled
    6. Task completes with payment-completed metadata
    """
    # Setup worker
    worker = ManifestWorker(manifest=paid_agent_manifest, storage=storage)
    
    # Create context and task
    context_id = uuid4()
    task_id = uuid4()
    
    # Create initial task with payment-required metadata (from Phase 1)
    initial_task: Task = {
        "kind": "task",
        "id": task_id,
        "context_id": context_id,
        "status": {
            "state": "input-required",
            "timestamp": "2025-01-01T00:00:00Z"
        },
        "history": [
            {
                "role": "user",
                "parts": [{"kind": "text", "text": "hello"}],
                "context_id": context_id,
                "task_id": task_id,
                "message_id": uuid4(),
            }
        ],
        "artifacts": [],
        "metadata": {
            app_settings.x402.meta_status_key: app_settings.x402.status_required,
            app_settings.x402.meta_required_key: {
                "x402Version": 1,
                "accepts": [{
                    "scheme": "exact",
                    "network": "base-sepolia",
                    "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                    "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
                    "maxAmountRequired": "1000000",
                }]
            }
        }
    }
    
    # Store initial task
    await storage.save_task(initial_task)
    
    # Submit payment payload (second request)
    payment_message = {
        "role": "user",
        "parts": [{"kind": "text", "text": "hello"}],
        "context_id": context_id,
        "task_id": task_id,
        "message_id": uuid4(),
        "metadata": {
            app_settings.x402.meta_status_key: app_settings.x402.status_submitted,
            app_settings.x402.meta_payload_key: {
                "resource": "/agent/test-paid-agent",
                "scheme": "exact",
                "network": "base-sepolia",
                "asset": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
                "payTo": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
                "amount": "1000000",
                "signature": "0xmocksignature",
                "timestamp": "2025-01-01T00:00:00Z"
            }
        }
    }
    
    # Add payment message to task history
    task_with_payment = await storage.load_task(task_id)
    task_with_payment["history"].append(payment_message)
    await storage.save_task(task_with_payment)
    
    # Execute task with payment
    params = {
        "task_id": task_id,
        "context_id": context_id,
        "message": payment_message
    }
    
    await worker.run_task(params)
    
    # Verify task completed successfully
    final_task = await storage.load_task(task_id)
    
    assert final_task is not None
    assert final_task["status"]["state"] == "completed"
    
    # Verify payment metadata
    metadata = final_task.get("metadata", {})
    assert metadata.get(app_settings.x402.meta_status_key) == app_settings.x402.status_completed
    assert app_settings.x402.meta_receipts_key in metadata
    
    receipts = metadata[app_settings.x402.meta_receipts_key]
    assert len(receipts) == 1
    assert receipts[0]["transactionHash"] == "0xabc123"
    assert receipts[0]["blockNumber"] == 12345
    
    # Verify agent was called
    paid_agent_manifest.run.assert_called_once()
    
    # Verify facilitator was called
    mock_facilitator_client.verify.assert_called_once()
    mock_facilitator_client.settle.assert_called_once()
    
    # Verify artifacts were created
    assert len(final_task.get("artifacts", [])) > 0


@pytest.mark.asyncio
@pytest.mark.x402
async def test_payment_verification_failure(storage, paid_agent_manifest):
    """Test payment verification failure.
    
    Flow:
    1. Create task with payment-required metadata
    2. Submit invalid payment payload
    3. Verify payment verification fails
    4. Task returns to input-required with payment-failed metadata
    5. Agent does NOT execute
    """
    # Mock facilitator to fail verification
    with patch("bindu.server.workers.manifest_worker.FacilitatorClient") as mock:
        instance = MagicMock()
        verify_response = MagicMock()
        verify_response.is_valid = False
        verify_response.invalid_reason = "invalid_signature"
        instance.verify = AsyncMock(return_value=verify_response)
        mock.return_value = instance
        
        # Setup worker
        worker = ManifestWorker(manifest=paid_agent_manifest, storage=storage)
        
        # Create context and task
        context_id = uuid4()
        task_id = uuid4()
        
        # Create task with payment submission
        task: Task = {
            "kind": "task",
            "id": task_id,
            "context_id": context_id,
            "status": {
                "state": "input-required",
                "timestamp": "2025-01-01T00:00:00Z"
            },
            "history": [
                {
                    "role": "user",
                    "parts": [{"kind": "text", "text": "hello"}],
                    "context_id": context_id,
                    "task_id": task_id,
                    "message_id": uuid4(),
                    "metadata": {
                        app_settings.x402.meta_status_key: app_settings.x402.status_submitted,
                        app_settings.x402.meta_payload_key: {
                            "resource": "/agent/test-paid-agent",
                            "signature": "0xinvalidsignature",
                        }
                    }
                }
            ],
            "artifacts": [],
            "metadata": {
                app_settings.x402.meta_required_key: {
                    "accepts": [{
                        "scheme": "exact",
                        "network": "base-sepolia",
                    }]
                }
            }
        }
        
        await storage.save_task(task)
        
        # Execute task
        params = {
            "task_id": task_id,
            "context_id": context_id,
            "message": task["history"][0]
        }
        
        await worker.run_task(params)
        
        # Verify task is still input-required
        final_task = await storage.load_task(task_id)
        assert final_task["status"]["state"] == "input-required"
        
        # Verify payment-failed metadata
        metadata = final_task.get("metadata", {})
        assert metadata.get(app_settings.x402.meta_status_key) == app_settings.x402.status_failed
        assert metadata.get(app_settings.x402.meta_error_key) == "invalid_signature"
        
        # Verify agent was NOT called
        paid_agent_manifest.run.assert_not_called()
        
        # Verify error message was added
        assert len(final_task["history"]) > 1
        last_message = final_task["history"][-1]
        assert last_message["role"] == "agent"
        assert "verification failed" in str(last_message["parts"][0]["text"]).lower()


@pytest.mark.asyncio
@pytest.mark.x402
async def test_payment_settlement_failure(storage, paid_agent_manifest):
    """Test payment settlement failure after successful execution.
    
    Flow:
    1. Payment verification succeeds
    2. Agent executes successfully
    3. Settlement fails
    4. Task returns to input-required with payment-failed metadata
    """
    # Mock facilitator: verify succeeds, settle fails
    with patch("bindu.server.workers.manifest_worker.FacilitatorClient") as mock:
        instance = MagicMock()
        
        # Verify succeeds
        verify_response = MagicMock()
        verify_response.is_valid = True
        instance.verify = AsyncMock(return_value=verify_response)
        
        # Settle fails
        settle_response = MagicMock()
        settle_response.success = False
        settle_response.error_reason = "insufficient_gas"
        settle_response.model_dump = MagicMock(return_value={
            "error": "insufficient_gas"
        })
        instance.settle = AsyncMock(return_value=settle_response)
        
        mock.return_value = instance
        
        # Setup worker
        worker = ManifestWorker(manifest=paid_agent_manifest, storage=storage)
        
        # Create context and task
        context_id = uuid4()
        task_id = uuid4()
        
        # Create task with payment submission
        task: Task = {
            "kind": "task",
            "id": task_id,
            "context_id": context_id,
            "status": {
                "state": "input-required",
                "timestamp": "2025-01-01T00:00:00Z"
            },
            "history": [
                {
                    "role": "user",
                    "parts": [{"kind": "text", "text": "hello"}],
                    "context_id": context_id,
                    "task_id": task_id,
                    "message_id": uuid4(),
                    "metadata": {
                        app_settings.x402.meta_status_key: app_settings.x402.status_submitted,
                        app_settings.x402.meta_payload_key: {
                            "resource": "/agent/test-paid-agent",
                            "scheme": "exact",
                            "network": "base-sepolia",
                            "signature": "0xvalidsignature",
                        }
                    }
                }
            ],
            "artifacts": [],
            "metadata": {
                app_settings.x402.meta_required_key: {
                    "accepts": [{
                        "scheme": "exact",
                        "network": "base-sepolia",
                    }]
                }
            }
        }
        
        await storage.save_task(task)
        
        # Execute task
        params = {
            "task_id": task_id,
            "context_id": context_id,
            "message": task["history"][0]
        }
        
        await worker.run_task(params)
        
        # Verify task is input-required (not completed)
        final_task = await storage.load_task(task_id)
        assert final_task["status"]["state"] == "input-required"
        
        # Verify payment-failed metadata
        metadata = final_task.get("metadata", {})
        assert metadata.get(app_settings.x402.meta_status_key) == app_settings.x402.status_failed
        assert "insufficient_gas" in metadata.get(app_settings.x402.meta_error_key, "")
        
        # Verify agent WAS called (execution happened before settlement)
        paid_agent_manifest.run.assert_called_once()
        
        # Verify NO artifacts (settlement failed, so task didn't complete)
        assert len(final_task.get("artifacts", [])) == 0
        
        # Verify error message was added
        last_message = final_task["history"][-1]
        assert last_message["role"] == "agent"
        assert "settlement failed" in str(last_message["parts"][0]["text"]).lower()


@pytest.mark.asyncio
@pytest.mark.x402
async def test_non_paid_agent_normal_flow(storage, free_agent_manifest):
    """Test that agents without execution_cost work normally.
    
    Flow:
    1. Agent without execution_cost
    2. Send message (no payment)
    3. Agent executes immediately
    4. Task completes normally
    """
    # Setup worker
    worker = ManifestWorker(manifest=free_agent_manifest, storage=storage)
    
    # Create context and task
    context_id = uuid4()
    task_id = uuid4()
    
    # Create normal task (no payment metadata)
    task: Task = {
        "kind": "task",
        "id": task_id,
        "context_id": context_id,
        "status": {
            "state": "submitted",
            "timestamp": "2025-01-01T00:00:00Z"
        },
        "history": [
            {
                "role": "user",
                "parts": [{"kind": "text", "text": "hello"}],
                "context_id": context_id,
                "task_id": task_id,
                "message_id": uuid4(),
            }
        ],
        "artifacts": [],
        "metadata": {}
    }
    
    await storage.save_task(task)
    
    # Execute task
    params = {
        "task_id": task_id,
        "context_id": context_id,
        "message": task["history"][0]
    }
    
    await worker.run_task(params)
    
    # Verify task completed
    final_task = await storage.load_task(task_id)
    assert final_task["status"]["state"] == "completed"
    
    # Verify NO payment metadata
    metadata = final_task.get("metadata", {})
    assert app_settings.x402.meta_status_key not in metadata
    
    # Verify agent was called
    free_agent_manifest.run.assert_called_once()
    
    # Verify artifacts were created
    assert len(final_task.get("artifacts", [])) > 0


@pytest.mark.asyncio
@pytest.mark.x402
async def test_payment_parsing_error(storage, paid_agent_manifest):
    """Test handling of malformed payment payload.
    
    Flow:
    1. Submit malformed payment payload
    2. Parsing fails
    3. Task returns to input-required with error
    """
    # Setup worker
    worker = ManifestWorker(manifest=paid_agent_manifest, storage=storage)
    
    # Create context and task
    context_id = uuid4()
    task_id = uuid4()
    
    # Create task with malformed payment
    task: Task = {
        "kind": "task",
        "id": task_id,
        "context_id": context_id,
        "status": {
            "state": "input-required",
            "timestamp": "2025-01-01T00:00:00Z"
        },
        "history": [
            {
                "role": "user",
                "parts": [{"kind": "text", "text": "hello"}],
                "context_id": context_id,
                "task_id": task_id,
                "message_id": uuid4(),
                "metadata": {
                    app_settings.x402.meta_status_key: app_settings.x402.status_submitted,
                    app_settings.x402.meta_payload_key: "invalid_payload_not_a_dict"
                }
            }
        ],
        "artifacts": [],
        "metadata": {}
    }
    
    await storage.save_task(task)
    
    # Execute task
    params = {
        "task_id": task_id,
        "context_id": context_id,
        "message": task["history"][0]
    }
    
    await worker.run_task(params)
    
    # Verify task is still input-required
    final_task = await storage.load_task(task_id)
    assert final_task["status"]["state"] == "input-required"
    
    # Verify agent was NOT called
    paid_agent_manifest.run.assert_not_called()
    
    # Verify error message was added
    assert len(final_task["history"]) > 1
    last_message = final_task["history"][-1]
    assert last_message["role"] == "agent"
