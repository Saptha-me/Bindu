"""Unit tests for DID Agent Extension."""

import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from bindu.extensions.did.did_agent_extension import DIDAgentExtension
from bindu.settings import app_settings


class TestDIDAgentExtension:
    """Test suite for DID Agent Extension."""

    @pytest.fixture
    def temp_key_dir(self):
        """Create a temporary directory for keys."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def did_extension(self, temp_key_dir):
        """Create a DID extension instance."""
        return DIDAgentExtension(
            recreate_keys=True,
            key_dir=temp_key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
        )

    def test_initialization(self, temp_key_dir):
        """Test DID extension initialization."""
        agent_id = str(uuid4())
        ext = DIDAgentExtension(
            recreate_keys=False,
            key_dir=temp_key_dir,
            author="alice@example.com",
            agent_name="travel_agent",
            agent_id=agent_id,
        )

        assert ext.author == "alice@example.com"
        assert ext.agent_name == "travel_agent"
        assert ext.agent_id == agent_id
        assert (
            ext.private_key_path == temp_key_dir / app_settings.did.private_key_filename
        )
        assert (
            ext.public_key_path == temp_key_dir / app_settings.did.public_key_filename
        )

    def test_initialization_with_password(self, temp_key_dir):
        """Test DID extension initialization with password."""
        ext = DIDAgentExtension(
            recreate_keys=False,
            key_dir=temp_key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
            key_password="test-password",
        )

        assert ext.key_password == b"test-password"

    def test_generate_and_save_key_pair(self, did_extension):
        """Test key pair generation and saving."""
        paths = did_extension.generate_and_save_key_pair()

        assert "private_key_path" in paths
        assert "public_key_path" in paths
        assert Path(paths["private_key_path"]).exists()
        assert Path(paths["public_key_path"]).exists()

    def test_generate_and_save_key_pair_skip_existing(self, did_extension):
        """Test that key generation is skipped if keys exist."""
        # Generate keys first time
        did_extension.generate_and_save_key_pair()

        # Create new extension with same dir, recreate_keys=False
        ext2 = DIDAgentExtension(
            recreate_keys=False,
            key_dir=did_extension._key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
        )

        # Should skip generation
        paths = ext2.generate_and_save_key_pair()
        assert Path(paths["private_key_path"]).exists()

    def test_generate_and_save_key_pair_recreate(self, did_extension):
        """Test that keys are recreated when recreate_keys=True."""
        # Generate keys first time
        did_extension.generate_and_save_key_pair()
        first_private_key = did_extension.private_key_path.read_bytes()

        # Create new extension with recreate_keys=True
        ext2 = DIDAgentExtension(
            recreate_keys=True,
            key_dir=did_extension._key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
        )

        # Should regenerate
        ext2.generate_and_save_key_pair()
        second_private_key = ext2.private_key_path.read_bytes()

        # Keys should be different
        assert first_private_key != second_private_key

    def test_load_private_key(self, did_extension):
        """Test loading private key from file."""
        did_extension.generate_and_save_key_pair()
        private_key = did_extension.private_key

        assert private_key is not None
        from cryptography.hazmat.primitives.asymmetric import ed25519

        assert isinstance(private_key, ed25519.Ed25519PrivateKey)

    def test_load_public_key(self, did_extension):
        """Test loading public key from file."""
        did_extension.generate_and_save_key_pair()
        public_key = did_extension.public_key

        assert public_key is not None
        from cryptography.hazmat.primitives.asymmetric import ed25519

        assert isinstance(public_key, ed25519.Ed25519PublicKey)

    def test_load_key_file_not_found(self, temp_key_dir):
        """Test error when key file doesn't exist."""
        ext = DIDAgentExtension(
            recreate_keys=False,
            key_dir=temp_key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
        )

        with pytest.raises(FileNotFoundError):
            _ = ext.private_key

    def test_sign_and_verify_text(self, did_extension):
        """Test signing and verifying text."""
        did_extension.generate_and_save_key_pair()

        text = "Hello, World!"
        signature = did_extension.sign_text(text)

        assert signature is not None
        assert isinstance(signature, str)
        assert did_extension.verify_text(text, signature) is True

    def test_verify_invalid_signature(self, did_extension):
        """Test verifying invalid signature."""
        did_extension.generate_and_save_key_pair()

        text = "Hello, World!"
        signature = did_extension.sign_text(text)

        # Verify with different text should fail
        assert did_extension.verify_text("Different text", signature) is False

    def test_verify_malformed_signature(self, did_extension):
        """Test verifying malformed signature."""
        did_extension.generate_and_save_key_pair()

        # Should return False for invalid signature
        assert did_extension.verify_text("test", "invalid-signature") is False

    def test_custom_did_format(self, temp_key_dir):
        """Test custom bindu DID format."""
        agent_id = "550e8400-e29b-41d4-a716-446655440000"
        ext = DIDAgentExtension(
            recreate_keys=True,
            key_dir=temp_key_dir,
            author="alice@example.com",
            agent_name="Travel Agent",
            agent_id=agent_id,
        )
        ext.generate_and_save_key_pair()

        did = ext.did
        assert did.startswith("did:bindu:")
        assert "alice_at_example_com" in did
        assert "travel_agent" in did
        assert agent_id in did

    def test_sanitize_did_component(self):
        """Test DID component sanitization."""
        assert DIDAgentExtension._sanitize_did_component("Test Agent") == "test_agent"
        assert (
            DIDAgentExtension._sanitize_did_component("user@example.com")
            == "user_at_example_com"
        )
        assert DIDAgentExtension._sanitize_did_component("agent.name") == "agent_name"

    def test_fallback_did_format(self, temp_key_dir):
        """Test fallback to did:key format when author/name not provided."""
        ext = DIDAgentExtension(
            recreate_keys=True,
            key_dir=temp_key_dir,
        )
        ext.generate_and_save_key_pair()

        did = ext.did
        assert did.startswith("did:key:")

    def test_get_did_document(self, did_extension):
        """Test generating DID document."""
        did_extension.generate_and_save_key_pair()

        doc = did_extension.get_did_document()

        assert "@context" in doc
        assert doc["id"] == did_extension.did
        assert "created" in doc
        assert "authentication" in doc
        assert len(doc["authentication"]) == 1
        assert (
            doc["authentication"][0]["type"] == app_settings.did.verification_key_type
        )

    def test_public_key_base58(self, did_extension):
        """Test base58-encoded public key."""
        did_extension.generate_and_save_key_pair()

        pub_key_b58 = did_extension.public_key_base58
        assert pub_key_b58 is not None
        assert isinstance(pub_key_b58, str)
        assert len(pub_key_b58) > 0

    def test_agent_extension_property(self, did_extension):
        """Test agent extension property."""
        did_extension.generate_and_save_key_pair()

        ext = did_extension.agent_extension

        assert ext["uri"] == app_settings.did.extension_uri
        assert ext["required"] is False
        assert "did" in ext["params"]
        assert ext["params"]["did"] == did_extension.did

    def test_encrypted_key_without_password(self, temp_key_dir):
        """Test loading encrypted key without password raises error."""
        # Create extension with password and generate keys
        ext1 = DIDAgentExtension(
            recreate_keys=True,
            key_dir=temp_key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
            key_password="test-password",
        )
        ext1.generate_and_save_key_pair()

        # Try to load with different extension without password
        ext2 = DIDAgentExtension(
            recreate_keys=False,
            key_dir=temp_key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
        )

        with pytest.raises(ValueError, match="Private key is encrypted"):
            _ = ext2.private_key

    def test_key_with_correct_password(self, temp_key_dir):
        """Test loading encrypted key with correct password."""
        password = "secure-password"

        # Create and save encrypted keys
        ext1 = DIDAgentExtension(
            recreate_keys=True,
            key_dir=temp_key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
            key_password=password,
        )
        ext1.generate_and_save_key_pair()

        # Load with same password
        ext2 = DIDAgentExtension(
            recreate_keys=False,
            key_dir=temp_key_dir,
            author="test@example.com",
            agent_name="test_agent",
            agent_id=str(uuid4()),
            key_password=password,
        )

        # Should load successfully
        private_key = ext2.private_key
        assert private_key is not None

    def test_file_permissions(self, did_extension):
        """Test that private key has correct file permissions."""
        did_extension.generate_and_save_key_pair()

        # Check private key permissions (should be 0o600)
        import stat

        private_key_stat = did_extension.private_key_path.stat()
        private_key_mode = stat.S_IMODE(private_key_stat.st_mode)
        assert private_key_mode == 0o600

        # Check public key permissions (should be 0o644)
        public_key_stat = did_extension.public_key_path.stat()
        public_key_mode = stat.S_IMODE(public_key_stat.st_mode)
        assert public_key_mode == 0o644
