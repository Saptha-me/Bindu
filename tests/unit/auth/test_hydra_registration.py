"""Tests for Hydra OAuth client registration utilities."""

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bindu.auth.hydra.registration import (
    save_agent_credentials,
    load_agent_credentials,
    register_agent_in_hydra,
)
from bindu.common.models import AgentCredentials


class TestSaveAgentCredentials:
    """Test saving agent OAuth credentials to disk."""

    def test_save_credentials_creates_directory(self):
        """Test that credentials directory is created if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir) / "nonexistent" / "nested"

            credentials = AgentCredentials(
                agent_id="agent-123",
                client_id="did:bindu:test",
                client_secret="secret",
                created_at=datetime.now(timezone.utc).isoformat(),
                scopes=["read", "write"],
            )

            save_agent_credentials(credentials, creds_dir)

            assert creds_dir.exists()
            assert (creds_dir / "oauth_credentials.json").exists()

    def test_save_credentials_creates_file(self):
        """Test that credentials file is created with correct data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)

            credentials = AgentCredentials(
                agent_id="agent-123",
                client_id="did:bindu:test",
                client_secret="secret",
                created_at=datetime.now(timezone.utc).isoformat(),
                scopes=["read", "write"],
            )

            save_agent_credentials(credentials, creds_dir)

            creds_file = creds_dir / "oauth_credentials.json"
            with open(creds_file, "r") as f:
                data = json.load(f)

            assert "did:bindu:test" in data
            assert data["did:bindu:test"]["client_id"] == "did:bindu:test"
            assert data["did:bindu:test"]["client_secret"] == "secret"

    def test_save_credentials_sets_restrictive_permissions(self):
        """Test that credentials file has restrictive permissions (0o600)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)

            credentials = AgentCredentials(
                agent_id="agent-123",
                client_id="did:bindu:test",
                client_secret="secret",
                created_at=datetime.now(timezone.utc).isoformat(),
                scopes=["read"],
            )

            save_agent_credentials(credentials, creds_dir)

            creds_file = creds_dir / "oauth_credentials.json"
            # Check permissions (owner read/write only) on non-Windows platforms
            if sys.platform != "win32":
                assert oct(creds_file.stat().st_mode)[-3:] == "600"

    def test_save_credentials_preserves_existing_entries(self):
        """Test that saving new credentials preserves existing ones."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)

            # Save first credential
            creds1 = AgentCredentials(
                agent_id="agent-1",
                client_id="did:bindu:agent1",
                client_secret="secret1",
                created_at=datetime.now(timezone.utc).isoformat(),
                scopes=["read"],
            )
            save_agent_credentials(creds1, creds_dir)

            # Save second credential
            creds2 = AgentCredentials(
                agent_id="agent-2",
                client_id="did:bindu:agent2",
                client_secret="secret2",
                created_at=datetime.now(timezone.utc).isoformat(),
                scopes=["write"],
            )
            save_agent_credentials(creds2, creds_dir)

            # Verify both exist
            creds_file = creds_dir / "oauth_credentials.json"
            with open(creds_file, "r") as f:
                data = json.load(f)

            assert "did:bindu:agent1" in data
            assert "did:bindu:agent2" in data

    def test_save_credentials_updates_existing_entry(self):
        """Test that saving credentials with same DID updates the entry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)

            # Save initial credential
            creds1 = AgentCredentials(
                agent_id="agent-1",
                client_id="did:bindu:test",
                client_secret="old-secret",
                created_at=datetime.now(timezone.utc).isoformat(),
                scopes=["read"],
            )
            save_agent_credentials(creds1, creds_dir)

            # Update with new secret
            creds2 = AgentCredentials(
                agent_id="agent-1",
                client_id="did:bindu:test",
                client_secret="new-secret",
                created_at=datetime.now(timezone.utc).isoformat(),
                scopes=["read", "write"],
            )
            save_agent_credentials(creds2, creds_dir)

            # Verify updated
            creds_file = creds_dir / "oauth_credentials.json"
            with open(creds_file, "r") as f:
                data = json.load(f)

            assert data["did:bindu:test"]["client_secret"] == "new-secret"
            assert len(data["did:bindu:test"]["scopes"]) == 2

    def test_save_credentials_handles_corrupted_file(self):
        """Test that corrupted credentials file is handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)
            creds_file = creds_dir / "oauth_credentials.json"

            # Create corrupted file
            creds_dir.mkdir(exist_ok=True)
            with open(creds_file, "w") as f:
                f.write("invalid json{")

            # Should still save successfully
            credentials = AgentCredentials(
                agent_id="agent-123",
                client_id="did:bindu:test",
                client_secret="secret",
                created_at=datetime.now(timezone.utc).isoformat(),
                scopes=["read"],
            )
            save_agent_credentials(credentials, creds_dir)

            # Verify new data saved
            with open(creds_file, "r") as f:
                data = json.load(f)
            assert "did:bindu:test" in data


class TestLoadAgentCredentials:
    """Test loading agent OAuth credentials from disk."""

    def test_load_credentials_success(self):
        """Test successfully loading existing credentials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)

            # Save credentials first
            credentials = AgentCredentials(
                agent_id="agent-123",
                client_id="did:bindu:test",
                client_secret="secret",
                created_at=datetime.now(timezone.utc).isoformat(),
                scopes=["read", "write"],
            )
            save_agent_credentials(credentials, creds_dir)

            # Load credentials
            loaded = load_agent_credentials("did:bindu:test", creds_dir)

            assert loaded is not None
            assert loaded.client_id == "did:bindu:test"
            assert loaded.client_secret == "secret"
            assert loaded.scopes == ["read", "write"]

    def test_load_credentials_file_not_exists(self):
        """Test loading credentials when file doesn't exist returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)

            result = load_agent_credentials("did:bindu:test", creds_dir)

            assert result is None

    def test_load_credentials_did_not_found(self):
        """Test loading credentials for non-existent DID returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)

            # Save credentials for different DID
            credentials = AgentCredentials(
                agent_id="agent-123",
                client_id="did:bindu:other",
                client_secret="secret",
                created_at=datetime.now(timezone.utc).isoformat(),
                scopes=["read"],
            )
            save_agent_credentials(credentials, creds_dir)

            # Try to load different DID
            result = load_agent_credentials("did:bindu:test", creds_dir)

            assert result is None

    def test_load_credentials_corrupted_file(self):
        """Test loading credentials from corrupted file returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)
            creds_file = creds_dir / "oauth_credentials.json"

            # Create corrupted file
            creds_dir.mkdir(exist_ok=True)
            with open(creds_file, "w") as f:
                f.write("invalid json{")

            result = load_agent_credentials("did:bindu:test", creds_dir)

            assert result is None


class TestRegisterAgentInHydra:
    """Test agent registration in Hydra."""

    @pytest.mark.asyncio
    async def test_register_agent_auto_registration_disabled(self):
        """Test registration skipped when auto-registration is disabled."""
        with patch("bindu.auth.hydra.registration.app_settings") as mock_settings:
            mock_settings.hydra.auto_register_agents = False

            result = await register_agent_in_hydra(
                agent_id="agent-123",
                agent_name="Test Agent",
                agent_url="http://localhost:3773",
                did="did:bindu:test",
                credentials_dir=Path("/tmp"),
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_register_agent_new_client_success(self):
        """Test successful registration of new agent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)

            mock_hydra = AsyncMock()
            mock_hydra.get_oauth_client = AsyncMock(return_value=None)
            mock_hydra.create_oauth_client = AsyncMock()
            mock_hydra.__aenter__ = AsyncMock(return_value=mock_hydra)
            mock_hydra.__aexit__ = AsyncMock()

            with patch("bindu.auth.hydra.registration.app_settings") as mock_settings:
                mock_settings.hydra.auto_register_agents = True
                mock_settings.hydra.admin_url = "http://localhost:4445"
                mock_settings.hydra.public_url = "http://localhost:4444"
                mock_settings.hydra.timeout = 10
                mock_settings.hydra.verify_ssl = True
                mock_settings.hydra.max_retries = 3
                mock_settings.hydra.default_grant_types = ["client_credentials"]
                mock_settings.hydra.default_agent_scopes = ["read", "write"]
                mock_settings.vault.enabled = False
                mock_settings.did.verification_key_type = "Ed25519VerificationKey2020"

                with patch(
                    "bindu.auth.hydra.registration.HydraClient", return_value=mock_hydra
                ):
                    result = await register_agent_in_hydra(
                        agent_id="agent-123",
                        agent_name="Test Agent",
                        agent_url="http://localhost:3773",
                        did="did:bindu:test",
                        credentials_dir=creds_dir,
                    )

            assert result is not None
            assert result.client_id == "did:bindu:test"
            assert result.agent_id == "agent-123"
            assert len(result.client_secret) > 0

    @pytest.mark.asyncio
    async def test_register_agent_existing_client_with_credentials(self):
        """Test registration when client exists with valid credentials."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)

            # Save existing credentials
            existing_creds = AgentCredentials(
                agent_id="agent-123",
                client_id="did:bindu:test",
                client_secret="existing-secret",
                created_at=datetime.now(timezone.utc).isoformat(),
                scopes=["read", "write"],
            )
            save_agent_credentials(existing_creds, creds_dir)

            mock_hydra = AsyncMock()
            mock_hydra.get_oauth_client = AsyncMock(
                return_value={"client_id": "did:bindu:test"}
            )
            mock_hydra.__aenter__ = AsyncMock(return_value=mock_hydra)
            mock_hydra.__aexit__ = AsyncMock()

            with patch("bindu.auth.hydra.registration.app_settings") as mock_settings:
                mock_settings.hydra.auto_register_agents = True
                mock_settings.hydra.admin_url = "http://localhost:4445"
                mock_settings.hydra.public_url = "http://localhost:4444"
                mock_settings.hydra.timeout = 10
                mock_settings.hydra.verify_ssl = True
                mock_settings.hydra.max_retries = 3
                mock_settings.vault.enabled = False

                with patch(
                    "bindu.auth.hydra.registration.HydraClient", return_value=mock_hydra
                ):
                    result = await register_agent_in_hydra(
                        agent_id="agent-123",
                        agent_name="Test Agent",
                        agent_url="http://localhost:3773",
                        did="did:bindu:test",
                        credentials_dir=creds_dir,
                    )

            assert result is not None
            assert result.client_secret == "existing-secret"

    @pytest.mark.asyncio
    async def test_register_agent_with_did_extension(self):
        """Test registration with DID extension for public key extraction."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)

            mock_did_extension = MagicMock()
            mock_did_extension.public_key_base58 = (
                "5D5sRMv58uwU5zWRv7zEeXJC3DRPkkNeqFC8ZbTHkTDeA"
            )

            mock_hydra = AsyncMock()
            mock_hydra.get_oauth_client = AsyncMock(return_value=None)
            mock_hydra.create_oauth_client = AsyncMock()
            mock_hydra.__aenter__ = AsyncMock(return_value=mock_hydra)
            mock_hydra.__aexit__ = AsyncMock()

            with patch("bindu.auth.hydra.registration.app_settings") as mock_settings:
                mock_settings.hydra.auto_register_agents = True
                mock_settings.hydra.admin_url = "http://localhost:4445"
                mock_settings.hydra.public_url = "http://localhost:4444"
                mock_settings.hydra.timeout = 10
                mock_settings.hydra.verify_ssl = True
                mock_settings.hydra.max_retries = 3
                mock_settings.hydra.default_grant_types = ["client_credentials"]
                mock_settings.hydra.default_agent_scopes = ["read"]
                mock_settings.vault.enabled = False
                mock_settings.did.verification_key_type = "Ed25519VerificationKey2020"

                with patch(
                    "bindu.auth.hydra.registration.HydraClient", return_value=mock_hydra
                ):
                    result = await register_agent_in_hydra(
                        agent_id="agent-123",
                        agent_name="Test Agent",
                        agent_url="http://localhost:3773",
                        did="did:bindu:test",
                        credentials_dir=creds_dir,
                        did_extension=mock_did_extension,
                    )

            assert result is not None
            # Verify create_oauth_client was called with public key in metadata
            call_args = mock_hydra.create_oauth_client.call_args[0][0]
            assert (
                call_args["metadata"]["public_key"]
                == "5D5sRMv58uwU5zWRv7zEeXJC3DRPkkNeqFC8ZbTHkTDeA"
            )
            assert call_args["metadata"]["key_type"] == "Ed25519"

    @pytest.mark.asyncio
    async def test_register_agent_existing_client_no_credentials_deletes_and_recreates(
        self,
    ):
        """Test that existing client without credentials is deleted and recreated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)

            mock_hydra = AsyncMock()
            mock_hydra.get_oauth_client = AsyncMock(
                return_value={"client_id": "did:bindu:test"}
            )
            mock_hydra.delete_oauth_client = AsyncMock()
            mock_hydra.create_oauth_client = AsyncMock()
            mock_hydra.__aenter__ = AsyncMock(return_value=mock_hydra)
            mock_hydra.__aexit__ = AsyncMock()

            with patch("bindu.auth.hydra.registration.app_settings") as mock_settings:
                mock_settings.hydra.auto_register_agents = True
                mock_settings.hydra.admin_url = "http://localhost:4445"
                mock_settings.hydra.public_url = "http://localhost:4444"
                mock_settings.hydra.timeout = 10
                mock_settings.hydra.verify_ssl = True
                mock_settings.hydra.max_retries = 3
                mock_settings.hydra.default_grant_types = ["client_credentials"]
                mock_settings.hydra.default_agent_scopes = ["read"]
                mock_settings.vault.enabled = False
                mock_settings.did.verification_key_type = "Ed25519VerificationKey2020"

                with patch(
                    "bindu.auth.hydra.registration.HydraClient", return_value=mock_hydra
                ):
                    await register_agent_in_hydra(
                        agent_id="agent-123",
                        agent_name="Test Agent",
                        agent_url="http://localhost:3773",
                        did="did:bindu:test",
                        credentials_dir=creds_dir,
                    )

            # Verify delete was called before create
            mock_hydra.delete_oauth_client.assert_called_once_with("did:bindu:test")
            mock_hydra.create_oauth_client.assert_called_once()

    @pytest.mark.asyncio
    async def test_register_agent_hydra_error_returns_none(self):
        """Test that Hydra errors during registration return None gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)

            mock_hydra = AsyncMock()
            mock_hydra.get_oauth_client = AsyncMock(
                side_effect=Exception("Connection error")
            )
            mock_hydra.__aenter__ = AsyncMock(return_value=mock_hydra)
            mock_hydra.__aexit__ = AsyncMock()

            with patch("bindu.auth.hydra.registration.app_settings") as mock_settings:
                mock_settings.hydra.auto_register_agents = True
                mock_settings.hydra.admin_url = "http://localhost:4445"
                mock_settings.hydra.public_url = "http://localhost:4444"
                mock_settings.hydra.timeout = 10
                mock_settings.hydra.verify_ssl = True
                mock_settings.hydra.max_retries = 3
                mock_settings.vault.enabled = False

                with patch(
                    "bindu.auth.hydra.registration.HydraClient", return_value=mock_hydra
                ):
                    result = await register_agent_in_hydra(
                        agent_id="agent-123",
                        agent_name="Test Agent",
                        agent_url="http://localhost:3773",
                        did="did:bindu:test",
                        credentials_dir=creds_dir,
                    )

            assert result is None


class TestRegistrationEdgeCases:
    """Test edge cases in registration flow."""

    def test_save_credentials_with_empty_scopes(self):
        """Test saving credentials with empty scopes list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)

            credentials = AgentCredentials(
                agent_id="agent-123",
                client_id="did:bindu:test",
                client_secret="secret",
                created_at=datetime.now(timezone.utc).isoformat(),
                scopes=[],
            )

            save_agent_credentials(credentials, creds_dir)
            loaded = load_agent_credentials("did:bindu:test", creds_dir)

            assert loaded is not None
            assert loaded.scopes == []

    def test_save_credentials_with_special_characters_in_did(self):
        """Test saving credentials with DID containing special characters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            creds_dir = Path(tmpdir)

            credentials = AgentCredentials(
                agent_id="agent-123",
                client_id="did:bindu:agent:test-123_special",
                client_secret="secret",
                created_at=datetime.now(timezone.utc).isoformat(),
                scopes=["read"],
            )

            save_agent_credentials(credentials, creds_dir)
            loaded = load_agent_credentials(
                "did:bindu:agent:test-123_special", creds_dir
            )

            assert loaded is not None
            assert loaded.client_id == "did:bindu:agent:test-123_special"
