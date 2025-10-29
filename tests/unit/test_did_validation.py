"""Unit tests for DID validation utilities."""

import pytest

from bindu.extensions.did.validation import DIDValidation
from bindu.settings import app_settings


class TestDIDValidation:
    """Test suite for DID validation utilities."""

    # Test validate_did_format
    def test_validate_empty_did(self):
        """Test validation of empty DID."""
        valid, error = DIDValidation.validate_did_format("")
        assert valid is False
        assert error == "DID cannot be empty"

    def test_validate_invalid_prefix(self):
        """Test validation of DID with invalid prefix."""
        valid, error = DIDValidation.validate_did_format("invalid:bindu:author:agent")
        assert valid is False
        assert f"DID must start with '{app_settings.did.prefix}'" in error

    def test_validate_invalid_pattern(self):
        """Test validation of DID with invalid pattern."""
        valid, error = DIDValidation.validate_did_format("did:")
        assert valid is False
        assert error == "DID format is invalid"

    def test_validate_too_few_parts(self):
        """Test validation of DID with too few parts."""
        valid, error = DIDValidation.validate_did_format("did:method")
        assert valid is False
        # Pattern check fails before parts check
        assert error == "DID format is invalid"

    def test_validate_bindu_did_invalid_format(self):
        """Test validation of bindu DID with invalid format."""
        valid, error = DIDValidation.validate_did_format("did:bindu:author")
        assert valid is False
        assert "bindu DID must have format" in error

    def test_validate_bindu_did_empty_author(self):
        """Test validation of bindu DID with empty author."""
        valid, error = DIDValidation.validate_did_format("did:bindu::agent")
        assert valid is False
        # Pattern check fails first for empty components
        assert "bindu DID must have format" in error

    def test_validate_bindu_did_empty_agent_name(self):
        """Test validation of bindu DID with empty agent name."""
        valid, error = DIDValidation.validate_did_format("did:bindu:author:")
        assert valid is False
        # Pattern check fails first for empty components
        assert "bindu DID must have format" in error

    def test_validate_valid_bindu_did(self):
        """Test validation of valid bindu DID."""
        valid, error = DIDValidation.validate_did_format("did:bindu:author:agent")
        assert valid is True
        assert error is None

    def test_validate_valid_key_did(self):
        """Test validation of valid did:key format."""
        valid, error = DIDValidation.validate_did_format(
            "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK"
        )
        assert valid is True
        assert error is None

    def test_validate_valid_web_did(self):
        """Test validation of valid did:web format."""
        valid, error = DIDValidation.validate_did_format("did:web:example.com")
        assert valid is True
        assert error is None

    # Test validate_did_document
    def test_validate_document_missing_context(self):
        """Test validation of DID document missing @context."""
        doc = {"id": "did:bindu:author:agent"}
        valid, errors = DIDValidation.validate_did_document(doc)
        assert valid is False
        assert "Missing @context field" in errors

    def test_validate_document_missing_id(self):
        """Test validation of DID document missing id."""
        doc = {"@context": ["https://www.w3.org/ns/did/v1"]}
        valid, errors = DIDValidation.validate_did_document(doc)
        assert valid is False
        assert "Missing id field" in errors

    def test_validate_document_invalid_did_in_id(self):
        """Test validation of DID document with invalid DID in id field."""
        doc = {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": "invalid:did",
        }
        valid, errors = DIDValidation.validate_did_document(doc)
        assert valid is False
        assert any("Invalid DID in id field" in err for err in errors)

    def test_validate_document_authentication_not_array(self):
        """Test validation of DID document with authentication not an array."""
        doc = {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": "did:bindu:author:agent",
            "authentication": "not-an-array",
        }
        valid, errors = DIDValidation.validate_did_document(doc)
        assert valid is False
        assert "Authentication must be an array" in errors

    def test_validate_document_authentication_item_not_object(self):
        """Test validation of DID document with authentication item not an object."""
        doc = {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": "did:bindu:author:agent",
            "authentication": ["not-an-object"],
        }
        valid, errors = DIDValidation.validate_did_document(doc)
        assert valid is False
        assert any("Authentication[0] must be an object" in err for err in errors)

    def test_validate_document_authentication_missing_type(self):
        """Test validation of DID document with authentication missing type."""
        doc = {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": "did:bindu:author:agent",
            "authentication": [{"controller": "did:bindu:author:agent"}],
        }
        valid, errors = DIDValidation.validate_did_document(doc)
        assert valid is False
        assert any("Authentication[0] missing type" in err for err in errors)

    def test_validate_document_authentication_missing_controller(self):
        """Test validation of DID document with authentication missing controller."""
        doc = {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": "did:bindu:author:agent",
            "authentication": [{"type": "Ed25519VerificationKey2020"}],
        }
        valid, errors = DIDValidation.validate_did_document(doc)
        assert valid is False
        assert any("Authentication[0] missing controller" in err for err in errors)

    def test_validate_valid_document(self):
        """Test validation of valid DID document."""
        doc = {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": "did:bindu:author:agent",
            "authentication": [
                {
                    "id": "did:bindu:author:agent#key-1",
                    "type": "Ed25519VerificationKey2020",
                    "controller": "did:bindu:author:agent",
                    "publicKeyBase58": "H3C2AVvLMv6gmMNam3uVAjZpfkcJCwDwnZn6z3wXmqPV",
                }
            ],
        }
        valid, errors = DIDValidation.validate_did_document(doc)
        assert valid is True
        assert len(errors) == 0

    def test_validate_document_without_authentication(self):
        """Test validation of DID document without authentication (optional)."""
        doc = {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": "did:bindu:author:agent",
        }
        valid, errors = DIDValidation.validate_did_document(doc)
        assert valid is True
        assert len(errors) == 0

    def test_validate_document_multiple_authentication_errors(self):
        """Test validation of DID document with multiple authentication errors."""
        doc = {
            "@context": ["https://www.w3.org/ns/did/v1"],
            "id": "did:bindu:author:agent",
            "authentication": [
                {"type": "Ed25519VerificationKey2020"},  # Missing controller
                {"controller": "did:bindu:author:agent"},  # Missing type
                "not-an-object",  # Not an object
            ],
        }
        valid, errors = DIDValidation.validate_did_document(doc)
        assert valid is False
        assert len(errors) >= 3

    # Test private validation methods
    def test_validate_empty(self):
        """Test _validate_empty method."""
        valid, error = DIDValidation._validate_empty("")
        assert valid is False
        assert error == "DID cannot be empty"

        valid, error = DIDValidation._validate_empty("did:bindu:author:agent")
        assert valid is True
        assert error is None

    def test_validate_prefix(self):
        """Test _validate_prefix method."""
        valid, error = DIDValidation._validate_prefix("invalid:bindu:author:agent")
        assert valid is False
        assert f"DID must start with '{app_settings.did.prefix}'" in error

        valid, error = DIDValidation._validate_prefix("did:bindu:author:agent")
        assert valid is True
        assert error is None

    def test_validate_pattern(self):
        """Test _validate_pattern method."""
        valid, error = DIDValidation._validate_pattern("did:")
        assert valid is False
        assert error == "DID format is invalid"

        valid, error = DIDValidation._validate_pattern("did:bindu:author:agent")
        assert valid is True
        assert error is None

    def test_validate_parts(self):
        """Test _validate_parts method."""
        # Test with a DID that passes pattern but has too few parts
        # Need at least 3 parts: did:method:identifier
        valid, error, parts = DIDValidation._validate_parts("did:x")
        assert valid is False
        assert f"DID must have at least {app_settings.did.min_parts} parts" in error
        assert parts == []

        valid, error, parts = DIDValidation._validate_parts("did:bindu:author:agent")
        assert valid is True
        assert error is None
        assert len(parts) == 4

    def test_validate_bindu_did(self):
        """Test _validate_bindu_did method."""
        valid, error = DIDValidation._validate_bindu_did(
            "did:bindu:author", ["did", "bindu", "author"]
        )
        assert valid is False
        assert "bindu DID must have format" in error

        valid, error = DIDValidation._validate_bindu_did(
            "did:bindu:author:agent", ["did", "bindu", "author", "agent"]
        )
        assert valid is True
        assert error is None

    def test_validate_bindu_did_empty_components_in_parts(self):
        """Test _validate_bindu_did with empty components in parts array."""
        # This tests the second validation path (len check and empty check)
        valid, error = DIDValidation._validate_bindu_did(
            "did:bindu:author:agent", ["did", "bindu", "", "agent"]
        )
        assert valid is False
        assert "Author and agent name cannot be empty" in error

        valid, error = DIDValidation._validate_bindu_did(
            "did:bindu:author:agent", ["did", "bindu", "author", ""]
        )
        assert valid is False
        assert "Author and agent name cannot be empty" in error

    def test_validate_required_field(self):
        """Test _validate_required_field method."""
        errors = []
        DIDValidation._validate_required_field({"id": "test"}, "id", errors)
        assert len(errors) == 0

        errors = []
        DIDValidation._validate_required_field({"id": "test"}, "missing", errors)
        assert len(errors) == 1
        assert "Missing missing field" in errors[0]

    def test_validate_did_field(self):
        """Test _validate_did_field method."""
        errors = []
        DIDValidation._validate_did_field(
            {"id": "did:bindu:author:agent"}, errors
        )
        assert len(errors) == 0

        errors = []
        DIDValidation._validate_did_field({"id": "invalid:did"}, errors)
        assert len(errors) == 1
        assert "Invalid DID in id field" in errors[0]

    def test_validate_authentication_item(self):
        """Test _validate_authentication_item method."""
        errors = []
        DIDValidation._validate_authentication_item(
            {
                "type": "Ed25519VerificationKey2020",
                "controller": "did:bindu:author:agent",
            },
            0,
            errors,
        )
        assert len(errors) == 0

        errors = []
        DIDValidation._validate_authentication_item("not-an-object", 0, errors)
        assert len(errors) == 1
        assert "Authentication[0] must be an object" in errors[0]

        errors = []
        DIDValidation._validate_authentication_item({"type": "test"}, 0, errors)
        assert len(errors) == 1
        assert "Authentication[0] missing controller" in errors[0]

    def test_validate_authentication(self):
        """Test _validate_authentication method."""
        errors = []
        DIDValidation._validate_authentication(
            {
                "authentication": [
                    {
                        "type": "Ed25519VerificationKey2020",
                        "controller": "did:bindu:author:agent",
                    }
                ]
            },
            errors,
        )
        assert len(errors) == 0

        errors = []
        DIDValidation._validate_authentication(
            {"authentication": "not-an-array"}, errors
        )
        assert len(errors) == 1
        assert "Authentication must be an array" in errors[0]

        errors = []
        DIDValidation._validate_authentication({}, errors)
        assert len(errors) == 0  # Authentication is optional
