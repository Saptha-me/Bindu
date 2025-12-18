"""Tests for long-running task notification system (Issue #69).

TDD approach: RED → GREEN → REFACTOR

These tests validate:
1. Storage webhook CRUD operations (memory and postgres)
2. Push manager persistence and initialization
3. Global webhook fallback logic
4. Artifact notification support
5. long_running flag in MessageSendConfiguration
"""

import pytest
from uuid import uuid4, UUID
from unittest.mock import AsyncMock, MagicMock

from bindu.common.protocol.types import PushNotificationConfig


# =============================================================================
# Storage Interface Tests
# =============================================================================

class TestWebhookStorageMemory:
    """Test webhook persistence in InMemoryStorage."""

    @pytest.mark.asyncio
    async def test_save_and_load_webhook_config(self, storage):
        """Test saving and loading a webhook configuration."""
        task_id = uuid4()
        config: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://example.com/webhook",
            "token": "secret_token_123",
        }
        
        await storage.save_webhook_config(task_id, config)
        loaded = await storage.load_webhook_config(task_id)
        
        assert loaded is not None
        assert loaded["url"] == config["url"]
        assert loaded["token"] == config["token"]

    @pytest.mark.asyncio
    async def test_load_nonexistent_webhook_config(self, storage):
        """Test loading a webhook config that doesn't exist."""
        task_id = uuid4()
        loaded = await storage.load_webhook_config(task_id)
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_webhook_config(self, storage):
        """Test deleting a webhook configuration."""
        task_id = uuid4()
        config: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://example.com/webhook",
        }
        
        await storage.save_webhook_config(task_id, config)
        await storage.delete_webhook_config(task_id)
        loaded = await storage.load_webhook_config(task_id)
        
        assert loaded is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_webhook_config(self, storage):
        """Test deleting a webhook config that doesn't exist (should not raise)."""
        task_id = uuid4()
        # Should not raise
        await storage.delete_webhook_config(task_id)

    @pytest.mark.asyncio
    async def test_load_all_webhook_configs(self, storage):
        """Test loading all webhook configurations."""
        task_id_1 = uuid4()
        task_id_2 = uuid4()
        config_1: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://example.com/webhook1",
        }
        config_2: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://example.com/webhook2",
        }
        
        await storage.save_webhook_config(task_id_1, config_1)
        await storage.save_webhook_config(task_id_2, config_2)
        
        all_configs = await storage.load_all_webhook_configs()
        
        assert len(all_configs) == 2
        assert task_id_1 in all_configs
        assert task_id_2 in all_configs

    @pytest.mark.asyncio
    async def test_update_existing_webhook_config(self, storage):
        """Test updating an existing webhook configuration."""
        task_id = uuid4()
        config_1: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://example.com/webhook1",
        }
        config_2: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://example.com/webhook2",
            "token": "new_token",
        }
        
        await storage.save_webhook_config(task_id, config_1)
        await storage.save_webhook_config(task_id, config_2)
        
        loaded = await storage.load_webhook_config(task_id)
        assert loaded["url"] == "https://example.com/webhook2"
        assert loaded["token"] == "new_token"


# =============================================================================
# Push Manager Persistence Tests (
# =============================================================================

class TestPushManagerPersistence:
    """Test PushNotificationManager with persistence support."""

    @pytest.mark.asyncio
    async def test_initialize_loads_persisted_configs(self):
        """Test that initialize() loads configs from storage."""
        from bindu.server.notifications.push_manager import PushNotificationManager
        
        task_id = uuid4()
        config: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://example.com/webhook",
        }
        
        # Create mock storage with persisted config
        mock_storage = AsyncMock()
        mock_storage.load_all_webhook_configs.return_value = {task_id: config}
        
        # Create mock manifest with push_notifications enabled
        mock_manifest = MagicMock()
        mock_manifest.capabilities = {"push_notifications": True}
        
        manager = PushNotificationManager(
            manifest=mock_manifest,
            storage=mock_storage
        )
        
        await manager.initialize()
        
        # Verify config was loaded
        mock_storage.load_all_webhook_configs.assert_called_once()
        assert manager.get_push_config(task_id) == config

    @pytest.mark.asyncio
    async def test_register_with_persist_saves_to_storage(self):
        """Test that register_push_config with persist=True saves to storage."""
        from bindu.server.notifications.push_manager import PushNotificationManager
        
        task_id = uuid4()
        config: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://example.com/webhook",
        }
        
        mock_storage = AsyncMock()
        mock_manifest = MagicMock()
        mock_manifest.capabilities = {"push_notifications": True}
        
        manager = PushNotificationManager(
            manifest=mock_manifest,
            storage=mock_storage
        )
        
        await manager.register_push_config(task_id, config, persist=True)
        
        mock_storage.save_webhook_config.assert_called_once_with(task_id, config)

    @pytest.mark.asyncio
    async def test_register_without_persist_does_not_save(self):
        """Test that register_push_config with persist=False doesn't save to storage."""
        from bindu.server.notifications.push_manager import PushNotificationManager
        
        task_id = uuid4()
        config: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://example.com/webhook",
        }
        
        mock_storage = AsyncMock()
        mock_manifest = MagicMock()
        mock_manifest.capabilities = {"push_notifications": True}
        
        manager = PushNotificationManager(
            manifest=mock_manifest,
            storage=mock_storage
        )
        
        await manager.register_push_config(task_id, config, persist=False)
        
        mock_storage.save_webhook_config.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_with_delete_from_storage(self):
        """Test that remove_push_config with delete_from_storage=True deletes from storage."""
        from bindu.server.notifications.push_manager import PushNotificationManager
        
        task_id = uuid4()
        config: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://example.com/webhook",
        }
        
        mock_storage = AsyncMock()
        mock_manifest = MagicMock()
        mock_manifest.capabilities = {"push_notifications": True}
        
        manager = PushNotificationManager(
            manifest=mock_manifest,
            storage=mock_storage
        )
        manager._push_notification_configs[task_id] = config
        
        await manager.remove_push_config(task_id, delete_from_storage=True)
        
        mock_storage.delete_webhook_config.assert_called_once_with(task_id)


# =============================================================================
# Global Webhook Fallback Tests 
# =============================================================================

class TestGlobalWebhookFallback:
    """Test global webhook configuration fallback."""

    def test_get_global_webhook_config_from_manifest(self):
        """Test getting global webhook config from manifest."""
        from bindu.server.notifications.push_manager import PushNotificationManager
        
        mock_manifest = MagicMock()
        mock_manifest.capabilities = {"push_notifications": True}
        mock_manifest.global_webhook_url = "https://global.example.com/webhook"
        mock_manifest.global_webhook_token = "global_token"
        
        manager = PushNotificationManager(manifest=mock_manifest)
        
        global_config = manager.get_global_webhook_config()
        
        assert global_config is not None
        assert global_config["url"] == "https://global.example.com/webhook"
        assert global_config["token"] == "global_token"

    def test_get_global_webhook_config_returns_none_when_not_configured(self):
        """Test global webhook returns None when not configured."""
        from bindu.server.notifications.push_manager import PushNotificationManager
        
        mock_manifest = MagicMock()
        mock_manifest.capabilities = {"push_notifications": True}
        mock_manifest.global_webhook_url = None
        
        manager = PushNotificationManager(manifest=mock_manifest)
        
        global_config = manager.get_global_webhook_config()
        
        assert global_config is None

    def test_get_effective_webhook_config_prefers_task_specific(self):
        """Test that task-specific config takes priority over global."""
        from bindu.server.notifications.push_manager import PushNotificationManager
        
        task_id = uuid4()
        task_config: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://task.example.com/webhook",
        }
        
        mock_manifest = MagicMock()
        mock_manifest.capabilities = {"push_notifications": True}
        mock_manifest.global_webhook_url = "https://global.example.com/webhook"
        
        manager = PushNotificationManager(manifest=mock_manifest)
        manager._push_notification_configs[task_id] = task_config
        
        effective = manager.get_effective_webhook_config(task_id)
        
        assert effective["url"] == "https://task.example.com/webhook"

    def test_get_effective_webhook_config_falls_back_to_global(self):
        """Test fallback to global config when no task-specific config."""
        from bindu.server.notifications.push_manager import PushNotificationManager
        
        task_id = uuid4()
        
        mock_manifest = MagicMock()
        mock_manifest.capabilities = {"push_notifications": True}
        mock_manifest.global_webhook_url = "https://global.example.com/webhook"
        mock_manifest.global_webhook_token = None
        
        manager = PushNotificationManager(manifest=mock_manifest)
        
        effective = manager.get_effective_webhook_config(task_id)
        
        assert effective is not None
        assert effective["url"] == "https://global.example.com/webhook"


# =============================================================================
# Artifact Notification Tests 
# =========================================================================

class TestArtifactNotifications:
    """Test artifact update notifications."""

    @pytest.mark.asyncio
    async def test_notify_artifact_sends_event(self):
        """Test that notify_artifact sends an artifact-update event."""
        from bindu.server.notifications.push_manager import PushNotificationManager
        
        task_id = uuid4()
        context_id = uuid4()
        config: PushNotificationConfig = {
            "id": uuid4(),
            "url": "https://example.com/webhook",
        }
        artifact = {
            "artifact_id": str(uuid4()),
            "name": "result.json",
            "parts": [{"kind": "text", "text": "result data"}],
        }
        
        mock_manifest = MagicMock()
        mock_manifest.capabilities = {"push_notifications": True}
        
        manager = PushNotificationManager(manifest=mock_manifest)
        manager._push_notification_configs[task_id] = config
        manager.notification_service.send_event = AsyncMock()
        
        await manager.notify_artifact(task_id, context_id, artifact)
        
        manager.notification_service.send_event.assert_called_once()
        call_args = manager.notification_service.send_event.call_args
        event = call_args[0][1]
        assert event["kind"] == "artifact-update"
        assert event["task_id"] == str(task_id)
        assert event["artifact"] == artifact


# =============================================================================
#  Protocol Type Tests
# =============================================================================

class TestMessageSendConfigurationLongRunning:
    """Test long_running flag in MessageSendConfiguration."""

    def test_long_running_flag_in_configuration(self):
        """Test that MessageSendConfiguration accepts long_running flag."""
        from bindu.common.protocol.types import MessageSendConfiguration
        
        config: MessageSendConfiguration = {
            "accepted_output_modes": ["application/json"],
            "long_running": True,
            "push_notification_config": {
                "id": uuid4(),
                "url": "https://example.com/webhook",
            },
        }
        
        assert config["long_running"] is True

    def test_long_running_flag_defaults_to_false(self):
        """Test that long_running defaults to False when not specified."""
        from bindu.common.protocol.types import MessageSendConfiguration
        
        config: MessageSendConfiguration = {
            "accepted_output_modes": ["application/json"],
        }
        
        # NotRequired fields return None when accessed with .get()
        assert config.get("long_running", False) is False


# =============================================================================
# AgentManifest Global Webhook Tests
# =============================================================================

class TestAgentManifestGlobalWebhook:
    """Test global webhook configuration in AgentManifest."""

    def test_agent_manifest_has_global_webhook_fields(self):
        """Test that AgentManifest has global_webhook_url and global_webhook_token."""
        from bindu.common.models import AgentManifest
        from bindu.extensions.did import DIDAgentExtension
        from bindu.common.protocol.types import AgentTrust, AgentCapabilities
        from uuid import uuid4
        
        # Create minimal required objects
        mock_did = MagicMock(spec=DIDAgentExtension)
        
        manifest = AgentManifest(
            id=uuid4(),
            name="test_agent",
            did_extension=mock_did,
            description="Test agent",
            url="http://localhost:3773",
            version="1.0.0",
            protocol_version="1.0.0",
            agent_trust={
                "identity_provider": "auth0",
                "inherited_roles": [],
                "creator_id": "test",
                "creation_timestamp": 0,
                "trust_verification_required": False,
                "allowed_operations": {},
            },
            capabilities={"push_notifications": True},
            skills=[],
            kind="agent",
            num_history_sessions=10,
            global_webhook_url="https://global.example.com/webhook",
            global_webhook_token="global_secret",
        )
        
        assert manifest.global_webhook_url == "https://global.example.com/webhook"
        assert manifest.global_webhook_token == "global_secret"
