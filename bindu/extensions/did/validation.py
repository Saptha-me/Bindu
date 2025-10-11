"""DID validation utilities for format and document validation."""

from __future__ import annotations

import re
from typing import Any

from bindu.settings import app_settings


class DIDValidation:
    """Validation utilities for DID formats and documents.

    Provides methods to validate DID strings according to W3C specifications
    and validate DID document structure for compliance.
    """

    # Regex patterns for DID validation (compiled once for performance)
    _DID_PATTERN = re.compile(r"^did:[a-z0-9]+:.+$", re.IGNORECASE)
    _BINDU_DID_PATTERN = re.compile(r"^did:bindu:[^:]+:[^:]+$", re.IGNORECASE)

    @staticmethod
    def _validate_empty(did: str) -> tuple[bool, str | None]:
        """Check if DID is empty."""
        if not did:
            return False, "DID cannot be empty"
        return True, None

    @staticmethod
    def _validate_prefix(did: str) -> tuple[bool, str | None]:
        """Check if DID has correct prefix."""
        if not did.startswith(app_settings.did.prefix):
            return False, f"DID must start with '{app_settings.did.prefix}'"
        return True, None

    @staticmethod
    def _validate_pattern(did: str) -> tuple[bool, str | None]:
        """Check if DID matches basic pattern."""
        if not DIDValidation._DID_PATTERN.match(did):
            return False, "DID format is invalid"
        return True, None

    @staticmethod
    def _validate_parts(did: str) -> tuple[bool, str | None, list[str]]:
        """Split and validate DID parts."""
        parts = did.split(
            ":", app_settings.did.bindu_parts - 1
        )  # Max 4 parts for bindu DIDs

        if len(parts) < app_settings.did.min_parts:
            return (
                False,
                f"DID must have at least {app_settings.did.min_parts} parts separated by ':'",
                [],
            )

        return True, None, parts

    @staticmethod
    def _validate_bindu_did(did: str, parts: list[str]) -> tuple[bool, str | None]:
        """Validate Bindu-specific DID format."""
        if not DIDValidation._BINDU_DID_PATTERN.match(did):
            return (
                False,
                f"bindu DID must have format did:{app_settings.did.method_bindu}:author:agent_name",
            )

        # Validate non-empty components
        if len(parts) != app_settings.did.bindu_parts or not parts[2] or not parts[3]:
            return False, "Author and agent name cannot be empty in bindu DID"

        return True, None

    @staticmethod
    def validate_did_format(did: str) -> tuple[bool, str | None]:
        """Validate DID format according to W3C spec.

        Args:
            did: The DID string to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Chain of validation checks
        for validator in [
            DIDValidation._validate_empty,
            DIDValidation._validate_prefix,
            DIDValidation._validate_pattern,
        ]:
            valid, error = validator(did)
            if not valid:
                return valid, error

        # Validate parts
        valid, error, parts = DIDValidation._validate_parts(did)
        if not valid:
            return valid, error

        # Method-specific validation
        method = parts[1]
        if method == app_settings.did.method_bindu:
            return DIDValidation._validate_bindu_did(did, parts)

        return True, None

    @staticmethod
    def _validate_required_field(
        did_doc: dict[str, Any], field: str, errors: list[str]
    ) -> None:
        """Validate a required field exists."""
        if field not in did_doc:
            errors.append(f"Missing {field} field")

    @staticmethod
    def _validate_did_field(did_doc: dict[str, Any], errors: list[str]) -> None:
        """Validate the id field contains a valid DID."""
        if "id" in did_doc:
            valid, error = DIDValidation.validate_did_format(did_doc["id"])
            if not valid:
                errors.append(f"Invalid DID in id field: {error}")

    @staticmethod
    def _validate_authentication_item(auth: Any, index: int, errors: list[str]) -> None:
        """Validate a single authentication item."""
        if not isinstance(auth, dict):
            errors.append(f"Authentication[{index}] must be an object")
            return

        required_fields = ["type", "controller"]
        for field in required_fields:
            if field not in auth:
                errors.append(f"Authentication[{index}] missing {field}")

    @staticmethod
    def _validate_authentication(did_doc: dict[str, Any], errors: list[str]) -> None:
        """Validate authentication array if present."""
        if "authentication" not in did_doc:
            return

        auth_list = did_doc["authentication"]
        if not isinstance(auth_list, list):
            errors.append("Authentication must be an array")
            return

        for i, auth in enumerate(auth_list):
            DIDValidation._validate_authentication_item(auth, i, errors)

    @staticmethod
    def validate_did_document(did_doc: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validate a DID document structure.

        Args:
            did_doc: The DID document dictionary

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors: list[str] = []

        # Validate required fields
        DIDValidation._validate_required_field(did_doc, "@context", errors)
        DIDValidation._validate_required_field(did_doc, "id", errors)

        # Validate DID format in id field
        DIDValidation._validate_did_field(did_doc, errors)

        # Validate authentication if present
        DIDValidation._validate_authentication(did_doc, errors)

        return len(errors) == 0, errors
